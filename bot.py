"""QE Trainer — a Telegram tutor bot that teaches Quality Engineering
from Jacob's own reference books, with adaptive sessions, spaced repetition,
a progress dashboard, and book-grounded Q&A (/ask).
"""
import logging
import os
from datetime import datetime
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import db
from content_loader import Curriculum

# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------
BASE = Path(__file__).parent

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(BASE / "logs" / "bot.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("qe-trainer")


def load_env():
    """Minimal .env loader (avoids an extra dependency)."""
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


load_env()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ASK_MODEL = os.environ.get("QE_ASK_MODEL", "claude-haiku-4-5-20251001")

CURR = Curriculum()
_retriever = None  # lazy-loaded on first /ask


def get_retriever():
    global _retriever
    if _retriever is None:
        from rag.retriever import Retriever
        _retriever = Retriever()
    return _retriever


# --------------------------------------------------------------------------
# Helpers — choosing what to teach next
# --------------------------------------------------------------------------

def next_new_topic_id(chat_id):
    """First topic in curriculum order the user hasn't completed yet."""
    done = db.get_completed_topic_ids(chat_id)
    for tid in CURR.ordered_topic_ids:
        if tid not in done:
            return tid
    return None  # everything done


def build_session_queue(chat_id, minutes):
    """Return a list of step dicts for a session of the requested length."""
    queue = []
    due = db.get_due_items(chat_id, limit=20)

    def add_review(item):
        parsed = CURR.parse_item_id(item["item_id"])
        if not parsed:
            return
        if parsed["kind"] == "flashcard":
            queue.append({"type": "flashcard", "item_id": item["item_id"],
                          "q": parsed["q"], "a": parsed["a"], "topic_id": parsed["topic"]["id"]})
        else:
            queue.append({"type": "quiz", "item_id": item["item_id"], "q": parsed["q"],
                          "choices": parsed["choices"], "answer": parsed["answer"],
                          "explanation": parsed.get("explanation", ""), "topic_id": parsed["topic"]["id"]})

    def add_topic(topic_id, n_fc, n_quiz):
        t = CURR.topic_by_id[topic_id]
        queue.append({"type": "lesson", "topic_id": topic_id})
        for i in range(min(n_fc, len(t.get("flashcards", [])))):
            c = t["flashcards"][i]
            queue.append({"type": "flashcard", "item_id": CURR.flashcard_item_id(topic_id, i),
                          "q": c["q"], "a": c["a"], "topic_id": topic_id})
        for i in range(min(n_quiz, len(t.get("quiz", [])))):
            q = t["quiz"][i]
            queue.append({"type": "quiz", "item_id": CURR.quiz_item_id(topic_id, i), "q": q["q"],
                          "choices": q["choices"], "answer": q["answer"],
                          "explanation": q.get("explanation", ""), "topic_id": topic_id})

    if minutes <= 5:
        # Quick review: a couple due items, or 1 fresh quiz if nothing's due.
        for item in due[:2]:
            add_review(item)
        if not queue:
            tid = next_new_topic_id(chat_id)
            if tid:
                add_topic(tid, 0, 1)
    elif minutes <= 15:
        for item in due[:2]:
            add_review(item)
        tid = next_new_topic_id(chat_id)
        if tid:
            add_topic(tid, 3, 1)
    else:  # 30+ : reviews + up to two new topics
        for item in due[:3]:
            add_review(item)
        added = 0
        done_now = set(db.get_completed_topic_ids(chat_id))
        for tid in CURR.ordered_topic_ids:
            if added >= 2:
                break
            if tid not in done_now:
                add_topic(tid, 3, 2)
                done_now.add(tid)
                added += 1
    return queue


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def lesson_text(topic_id):
    t = CURR.topic_by_id[topic_id]
    emoji = CURR.module_emoji(t["module"])
    kp = "\n".join(f"• {p}" for p in t.get("key_points", []))
    parts = [
        f"{emoji} *{md(t['title'])}*",
        f"_{md(t['source'])}_",
        "",
        md(t["summary"]),
        "",
        f"*Key points*\n{md(kp)}",
    ]
    media = t.get("media", {})
    if media.get("web_notes"):
        parts += ["", f"🌐 *Deep dive*\n{md(media['web_notes'])}"]
    sources = media.get("sources", [])
    if sources:
        links = "\n".join(f"• [{md(s['title'])}]({s['url']})" for s in sources)
        parts += ["", f"*Sources*\n{links}"]
    return "\n".join(parts)


def md(text):
    """Escape Telegram MarkdownV2 special characters."""
    if text is None:
        return ""
    for ch in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, "\\" + ch)
    return text


def bar(frac, width=10):
    filled = round(frac * width)
    return "█" * filled + "░" * (width - filled)


# --------------------------------------------------------------------------
# Session stepping
# --------------------------------------------------------------------------

async def present_next(update_or_query, context):
    """Pop the next step from the queue and present it."""
    queue = context.user_data.get("queue", [])
    chat_id = context.user_data["chat_id"]

    if not queue:
        await send(update_or_query, context,
                   md("✅ Session complete! Use /progress to see your dashboard, "
                      "or /today to keep going."))
        return

    step = queue.pop(0)
    context.user_data["queue"] = queue

    if step["type"] == "lesson":
        db.mark_topic_seen(chat_id, step["topic_id"])
        await send_lesson(context, chat_id, step["topic_id"])

    elif step["type"] == "flashcard":
        context.user_data["current"] = step
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Show answer", callback_data="fc:reveal")]])
        await send(update_or_query, context,
                   f"🧠 *Flashcard*\n\n{md(step['q'])}", kb)

    elif step["type"] == "quiz":
        context.user_data["current"] = step
        letters = ["A", "B", "C", "D"]
        rows = [[InlineKeyboardButton(f"{letters[i]}. {c[:60]}", callback_data=f"quiz:{letters[i]}")]
                for i, c in enumerate(step["choices"])]
        await send(update_or_query, context,
                   f"❓ *Quiz*\n\n{md(step['q'])}", InlineKeyboardMarkup(rows))


async def send(update_or_query, context, text, reply_markup=None):
    """Send a MarkdownV2 message whether we're handling a command or a callback."""
    chat_id = context.user_data["chat_id"]
    await context.bot.send_message(
        chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup, disable_web_page_preview=True,
    )


async def send_lesson(context, chat_id, topic_id):
    """Present a lesson with its media: photo first, then text, then a video card.

    The 'Got it →' button that advances the session is always attached to the
    LAST message so the flow reads image → lesson → video → continue.
    """
    t = CURR.topic_by_id[topic_id]
    media = t.get("media", {})

    # 1) primary visual: a generated diagram or a figure pulled from the books
    img = media.get("image")
    if img and (BASE / img).exists():
        try:
            with open(BASE / img, "rb") as fh:
                await context.bot.send_photo(
                    chat_id=chat_id, photo=fh,
                    caption=(media.get("image_caption") or t["title"])[:1024])
        except Exception as e:
            log.warning("send_photo failed for %s: %s", img, e)

    next_btn = InlineKeyboardButton("Got it →", callback_data="step:next")
    video = media.get("video") or {}

    if video.get("url"):
        # lesson body without a button, then a video card carrying both buttons
        await context.bot.send_message(
            chat_id=chat_id, text=lesson_text(topic_id),
            parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
        vkb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"▶️ {video.get('title', 'Watch')[:32]}", url=video["url"])],
            [next_btn],
        ])
        await context.bot.send_message(
            chat_id=chat_id, text=f"🎥 _Watch to go deeper:_\n{md(video['url'])}",
            parse_mode=ParseMode.MARKDOWN_V2, reply_markup=vkb,
            disable_web_page_preview=False)
    else:
        await context.bot.send_message(
            chat_id=chat_id, text=lesson_text(topic_id),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([[next_btn]]),
            disable_web_page_preview=True)


# --------------------------------------------------------------------------
# Command handlers
# --------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.user_data["chat_id"] = chat_id
    db.get_or_create_user(chat_id)
    n_topics = len(CURR.ordered_topic_ids)
    text = (
        "👋 *Welcome to your QE Trainer*\n\n"
        f"I'll coach you toward a Quality Engineer role using your own books — "
        f"{n_topics} lessons across GD\\&T, SPC, FMEA, APQP, problem solving, vision systems, and physics/materials\\.\n\n"
        "*Commands*\n"
        "/today — adaptive study session \\(pick your time\\)\n"
        "/quiz — one quick quiz question\n"
        "/progress — your dashboard \\(streak, mastery\\)\n"
        "/topic — jump to a specific area\n"
        "/ask — ask anything; I answer from your books\n"
        "/settime — set your daily reminder time\n"
        "/help — show this again\n\n"
        "Start with /today 👇"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Start today's session", callback_data="today:prompt")],
        [InlineKeyboardButton("📊 See my progress", callback_data="show:progress")],
    ])
    await context.bot.send_message(chat_id=chat_id, text=text,
                                   parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["chat_id"] = update.effective_chat.id
    await cmd_start(update, context)


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["chat_id"] = update.effective_chat.id
    db.get_or_create_user(update.effective_chat.id)
    await prompt_time(update.effective_chat.id, context)


async def prompt_time(chat_id, context):
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("⚡ 5 min", callback_data="today:5"),
        InlineKeyboardButton("📖 15 min", callback_data="today:15"),
        InlineKeyboardButton("🔥 30 min", callback_data="today:30"),
    ]])
    await context.bot.send_message(
        chat_id=chat_id,
        text=md("How much time do you have today? I'll size the session to fit."),
        parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)


async def start_session(chat_id, minutes, context):
    context.user_data["chat_id"] = chat_id
    db.record_activity(chat_id)
    queue = build_session_queue(chat_id, minutes)
    context.user_data["queue"] = queue
    if not queue:
        await context.bot.send_message(
            chat_id=chat_id,
            text=md("🎉 You've completed every lesson! Use /quiz to keep your "
                    "spaced-repetition reviews sharp, or /ask to go deeper."),
            parse_mode=ParseMode.MARKDOWN_V2)
        return
    streak = db.get_streak(chat_id)
    await context.bot.send_message(
        chat_id=chat_id,
        text=md(f"🔥 {streak}-day streak • {len(queue)} items queued. Let's go!"),
        parse_mode=ParseMode.MARKDOWN_V2)
    await present_next(None, context)


async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.user_data["chat_id"] = chat_id
    db.get_or_create_user(chat_id)
    db.record_activity(chat_id)
    # one due item, else a fresh quiz from the next new topic
    due = db.get_due_items(chat_id, item_type="quiz", limit=1)
    queue = []
    if due:
        parsed = CURR.parse_item_id(due[0]["item_id"])
        if parsed:
            queue.append({"type": "quiz", "item_id": due[0]["item_id"], "q": parsed["q"],
                          "choices": parsed["choices"], "answer": parsed["answer"],
                          "explanation": parsed.get("explanation", ""),
                          "topic_id": parsed["topic"]["id"]})
    if not queue:
        tid = next_new_topic_id(chat_id) or CURR.ordered_topic_ids[0]
        t = CURR.topic_by_id[tid]
        q = t["quiz"][0]
        queue.append({"type": "quiz", "item_id": CURR.quiz_item_id(tid, 0), "q": q["q"],
                      "choices": q["choices"], "answer": q["answer"],
                      "explanation": q.get("explanation", ""), "topic_id": tid})
    context.user_data["queue"] = queue
    await present_next(None, context)


async def cmd_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.user_data["chat_id"] = chat_id
    await show_progress(chat_id, context)


async def show_progress(chat_id, context):
    done = db.get_completed_topic_ids(chat_id)
    streak = db.get_streak(chat_id)
    lines = ["📊 *Your QE Progress*\n"]
    total_done = 0
    for module in CURR.module_order:
        topics = CURR.topics_by_module[module]
        m_done = sum(1 for t in topics if t["id"] in done)
        total_done += m_done
        frac = m_done / len(topics) if topics else 0
        correct, attempts = db.get_accuracy(chat_id, CURR.all_item_ids_for_module(module))
        acc = f" • {round(100*correct/attempts)}% acc" if attempts else ""
        lines.append(
            f"{CURR.module_emoji(module)} {md(module)}\n"
            f"`{bar(frac)}` {m_done}/{len(topics)}{md(acc)}")
    total = len(CURR.ordered_topic_ids)
    overall = total_done / total if total else 0
    lines.append(f"\n*Overall* `{bar(overall)}` {total_done}/{total} lessons")
    lines.append(f"🔥 *Streak:* {streak} day\\(s\\)")
    nxt = next_new_topic_id(chat_id)
    if nxt:
        lines.append(f"\n*Up next:* {md(CURR.topic_by_id[nxt]['title'])}")
    else:
        lines.append("\n🎉 *All lessons complete — keep reviewing\\!*")
    await context.bot.send_message(chat_id=chat_id, text="\n".join(lines),
                                   parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.user_data["chat_id"] = chat_id
    rows = [[InlineKeyboardButton(f"{CURR.module_emoji(m)} {CURR.topics_by_module[m][0]['module']}",
                                  callback_data=f"mod:{m}")] for m in CURR.module_order]
    await context.bot.send_message(
        chat_id=chat_id, text=md("Pick an area to study:"),
        parse_mode=ParseMode.MARKDOWN_V2, reply_markup=InlineKeyboardMarkup(rows))


async def cmd_settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.user_data["chat_id"] = chat_id
    db.get_or_create_user(chat_id)
    arg = " ".join(context.args).strip() if context.args else ""
    try:
        datetime.strptime(arg, "%H:%M")
    except ValueError:
        await context.bot.send_message(
            chat_id=chat_id,
            text=md("Usage: /settime HH:MM  (24-hour, e.g. /settime 07:30)"),
            parse_mode=ParseMode.MARKDOWN_V2)
        return
    db.set_notify_time(chat_id, arg)
    await context.bot.send_message(
        chat_id=chat_id, text=md(f"⏰ Daily reminder set for {arg}."),
        parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.user_data["chat_id"] = chat_id
    question = " ".join(context.args).strip() if context.args else ""
    if not question:
        await context.bot.send_message(
            chat_id=chat_id,
            text=md("Ask me anything from your books, e.g.\n"
                    "/ask explain bonus tolerance in GD&T\n"
                    "/ask what's the difference between Cp and Cpk"),
            parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not ANTHROPIC_API_KEY:
        await context.bot.send_message(
            chat_id=chat_id,
            text=md("⚠️ /ask needs an ANTHROPIC_API_KEY in the .env file. "
                    "See the README to set one up."),
            parse_mode=ParseMode.MARKDOWN_V2)
        return
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    try:
        answer = await answer_with_books(question)
    except Exception as e:
        log.exception("ask failed")
        answer = f"Sorry, I hit an error answering that: {e}"
    await context.bot.send_message(chat_id=chat_id, text=md(answer),
                                   parse_mode=ParseMode.MARKDOWN_V2,
                                   disable_web_page_preview=True)


async def answer_with_books(question):
    """RAG: retrieve book chunks, then have Claude answer grounded in them."""
    import anthropic
    hits = get_retriever().search(question, k=5)
    if not hits:
        context_block = "(no relevant passages found in the books)"
        sources = []
    else:
        context_block = "\n\n".join(
            f"[{i+1}] ({h['book']}, p.{h['page']})\n{h['text']}" for i, h in enumerate(hits))
        sources = sorted({f"{h['book']} (p.{h['page']})" for h in hits})

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    system = (
        "You are a Quality Engineering tutor for someone training for a QE role. "
        "Answer the question using the provided book excerpts as your primary source. "
        "Be concise and practical (a few short paragraphs or bullets max). "
        "If the excerpts don't cover it, answer from general QE knowledge but say so. "
        "Use plain text (no markdown headers)."
    )
    msg = client.messages.create(
        model=ASK_MODEL,
        max_tokens=700,
        system=system,
        messages=[{
            "role": "user",
            "content": f"Question: {question}\n\nBook excerpts:\n{context_block}",
        }],
    )
    text = msg.content[0].text.strip()
    if sources:
        text += "\n\n📚 Sources: " + "; ".join(sources)
    return text


# --------------------------------------------------------------------------
# Callback (button) handler
# --------------------------------------------------------------------------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    context.user_data["chat_id"] = chat_id
    data = query.data

    if data == "today:prompt":
        await prompt_time(chat_id, context)
    elif data.startswith("today:"):
        minutes = int(data.split(":")[1])
        await start_session(chat_id, minutes, context)
    elif data == "show:progress":
        await show_progress(chat_id, context)
    elif data == "step:next":
        await present_next(query, context)
    elif data == "fc:reveal":
        step = context.user_data.get("current", {})
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Knew it", callback_data="fc:1"),
            InlineKeyboardButton("❌ Missed it", callback_data="fc:0"),
        ]])
        await context.bot.send_message(
            chat_id=chat_id, text=f"💡 *Answer*\n\n{md(step.get('a',''))}",
            parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)
    elif data in ("fc:1", "fc:0"):
        step = context.user_data.get("current", {})
        quality = 5 if data == "fc:1" else 2
        db.record_review_result(chat_id, step["item_id"], "flashcard", quality)
        await present_next(query, context)
    elif data.startswith("quiz:"):
        chosen = data.split(":")[1]
        step = context.user_data.get("current", {})
        correct_letter = step.get("answer")
        is_correct = chosen == correct_letter
        db.record_review_result(chat_id, step["item_id"], "quiz", 5 if is_correct else 2)
        verdict = "✅ Correct\\!" if is_correct else f"❌ Not quite — the answer is *{correct_letter}*\\."
        expl = step.get("explanation", "")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Next →", callback_data="step:next")]])
        await context.bot.send_message(
            chat_id=chat_id, text=f"{verdict}\n\n{md(expl)}",
            parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)
    elif data.startswith("mod:"):
        module = data.split(":", 1)[1]
        # queue the first not-done topic of that module (or the first topic)
        done = db.get_completed_topic_ids(chat_id)
        topics = CURR.topics_by_module[module]
        target = next((t for t in topics if t["id"] not in done), topics[0])
        t = target
        queue = [{"type": "lesson", "topic_id": t["id"]}]
        for i in range(min(3, len(t.get("flashcards", [])))):
            c = t["flashcards"][i]
            queue.append({"type": "flashcard", "item_id": CURR.flashcard_item_id(t["id"], i),
                          "q": c["q"], "a": c["a"], "topic_id": t["id"]})
        if t.get("quiz"):
            q = t["quiz"][0]
            queue.append({"type": "quiz", "item_id": CURR.quiz_item_id(t["id"], 0), "q": q["q"],
                          "choices": q["choices"], "answer": q["answer"],
                          "explanation": q.get("explanation", ""), "topic_id": t["id"]})
        context.user_data["queue"] = queue
        db.record_activity(chat_id)
        await present_next(query, context)


# --------------------------------------------------------------------------
# Daily reminder scheduler
# --------------------------------------------------------------------------
_last_notified = {}  # chat_id -> date string, to avoid double-sending


async def reminder_tick(app):
    now = datetime.now()
    hhmm = now.strftime("%H:%M")
    today = now.strftime("%Y-%m-%d")
    for user in db.get_all_users():
        cid = user["chat_id"]
        if user["notify_time"] == hhmm and _last_notified.get(cid) != today:
            _last_notified[cid] = today
            try:
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("⚡ 5", callback_data="today:5"),
                    InlineKeyboardButton("📖 15", callback_data="today:15"),
                    InlineKeyboardButton("🔥 30", callback_data="today:30"),
                ]])
                streak = db.get_streak(cid)
                await app.bot.send_message(
                    chat_id=cid,
                    text=md(f"☀️ Good morning! Ready for today's QE training? "
                            f"({streak}-day streak) — how much time?"),
                    parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb)
            except Exception:
                log.exception("reminder send failed for %s", cid)


async def post_init(app: Application):
    db.init_db()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(reminder_tick, "interval", seconds=60, args=[app])
    scheduler.start()
    log.info("Scheduler started; bot ready. %d topics loaded.", len(CURR.ordered_topic_ids))


def main():
    if not TELEGRAM_TOKEN:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and add your token "
            "(see README.md).")
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("quiz", cmd_quiz))
    app.add_handler(CommandHandler("progress", cmd_progress))
    app.add_handler(CommandHandler("topic", cmd_topic))
    app.add_handler(CommandHandler("settime", cmd_settime))
    app.add_handler(CommandHandler("ask", cmd_ask))
    app.add_handler(CallbackQueryHandler(on_callback))
    log.info("Starting QE Trainer bot (polling)…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
