"""QE Trainer PWA — Flask backend.

Wraps the EXISTING curriculum (content/*.json), spaced-repetition store (db.py),
and media assets behind a small JSON API, and serves the installable web app.
Single user (it's just for Jacob), so we use a fixed USER_ID.

Run locally:  python3 webapp/server.py   ->  http://localhost:8000
"""
import os
import random
import re
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, send_file

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))


def _load_env():
    """Load BASE/.env into the environment (the PWA isn't started via the bot's loader)."""
    env = BASE / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


_load_env()

import db
from content_loader import Curriculum

USER_ID = 1                       # single-user app
COURSE_TITLE = "Tesla QE Academy"
STATIC = Path(__file__).parent / "static"
MEDIA = BASE / "media"

db.init_db()
db.get_or_create_user(USER_ID)
CURR = Curriculum()

app = Flask(__name__, static_folder=None)

# lazy RAG (only if an Anthropic key is configured)
_retriever = None


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _embed(url):
    """Turn a YouTube watch/short URL into an embeddable one."""
    if not url:
        return None
    m = re.search(r"(?:v=|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})", url)
    return f"https://www.youtube.com/embed/{m.group(1)}" if m else None


def _media_url(rel):
    """'media/diagrams/x.png' -> '/media/diagrams/x.png' (served below)."""
    if not rel:
        return None
    rel = rel[len("media/"):] if rel.startswith("media/") else rel
    return f"/media/{rel}"


def _topic_media(t):
    m = t.get("media", {}) or {}
    video = m.get("video") or {}
    return {
        "image": _media_url(m.get("image")),
        "image_caption": m.get("image_caption"),
        "video": {"title": video.get("title"), "url": video.get("url"),
                  "embed": _embed(video.get("url"))} if video.get("url") else None,
        "web_notes": m.get("web_notes"),
        "sources": m.get("sources", []),
    }


# --------------------------------------------------------------------------
# app shell + static assets + media
# --------------------------------------------------------------------------
@app.route("/")
def index():
    return send_file(STATIC / "index.html")


@app.route("/<path:fname>")
def static_files(fname):
    # serve files that live directly in static/ (app.js, styles.css, manifest, sw.js, icons/)
    target = STATIC / fname
    if target.is_file():
        return send_from_directory(STATIC, fname)
    return ("Not found", 404)


@app.route("/media/<path:relpath>")
def media(relpath):
    return send_from_directory(MEDIA, relpath)


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
@app.route("/api/course")
def api_course():
    done = db.get_completed_topic_ids(USER_ID)
    modules = []
    total_topics = total_done = 0
    for mid in CURR.module_order:
        topics = CURR.topics_by_module[mid]
        t_done = sum(1 for t in topics if t["id"] in done)
        total_topics += len(topics)
        total_done += t_done
        modules.append({
            "id": mid,
            "emoji": CURR.module_emoji(mid),
            "title": CURR.module_title(mid),
            "lesson_count": len(topics),
            "done_count": t_done,
            "topics": [{"id": t["id"], "title": t["title"],
                        "done": t["id"] in done,
                        "has_media": bool(t.get("media"))} for t in topics],
        })
    return jsonify({
        "title": COURSE_TITLE,
        "modules": modules,
        "total_topics": total_topics,
        "total_done": total_done,
        "streak": db.get_streak(USER_ID),
    })


@app.route("/api/topic/<tid>")
def api_topic(tid):
    t = CURR.topic_by_id.get(tid)
    if not t:
        return jsonify({"error": "not found"}), 404
    mid = t["module"]
    seq = CURR.topics_by_module[mid]
    idx = next(i for i, x in enumerate(seq) if x["id"] == tid)
    g = CURR.ordered_topic_ids
    gi = g.index(tid)
    done = db.get_completed_topic_ids(USER_ID)
    return jsonify({
        "id": tid,
        "title": t["title"],
        "source": t["source"],
        "module": mid,
        "module_title": CURR.module_title(mid),
        "module_emoji": CURR.module_emoji(mid),
        "lesson_index": idx + 1,
        "lesson_count": len(seq),
        "summary": t["summary"],
        "reading": t.get("reading"),
        "key_points": t.get("key_points", []),
        "case_study": t.get("case_study"),
        "critical_thinking": t.get("critical_thinking", []),
        "media": _topic_media(t),
        "flashcards": [{"id": CURR.flashcard_item_id(tid, i), **c}
                       for i, c in enumerate(t.get("flashcards", []))],
        "quiz": [{"id": CURR.quiz_item_id(tid, i), **q}
                 for i, q in enumerate(t.get("quiz", []))],
        "done": tid in done,
        "prev_id": g[gi - 1] if gi > 0 else None,
        "next_id": g[gi + 1] if gi < len(g) - 1 else None,
    })


@app.route("/api/topic/<tid>/complete", methods=["POST"])
def api_complete(tid):
    if tid not in CURR.topic_by_id:
        return jsonify({"error": "not found"}), 404
    db.mark_topic_seen(USER_ID, tid)
    db.record_activity(USER_ID)
    return jsonify({"ok": True})


@app.route("/api/answer", methods=["POST"])
def api_answer():
    d = request.get_json(force=True)
    item_id, item_type, quality = d["item_id"], d["item_type"], int(d["quality"])
    db.record_review_result(USER_ID, item_id, item_type, quality)
    db.record_activity(USER_ID)
    return jsonify({"ok": True})


@app.route("/api/review")
def api_review():
    rows = db.get_due_items(USER_ID, None, limit=30)
    items = []
    for r in rows:
        parsed = CURR.parse_item_id(r["item_id"])
        if not parsed:
            continue
        items.append({"item_id": r["item_id"], "item_type": r["item_type"],
                      "topic_id": parsed["topic"]["id"],
                      "topic_title": parsed["topic"]["title"], **{k: v for k, v in parsed.items()
                                                                  if k != "topic"}})
    return jsonify({"items": items, "due_count": len(items)})


@app.route("/api/progress")
def api_progress():
    done = db.get_completed_topic_ids(USER_ID)
    mods = []
    for mid in CURR.module_order:
        topics = CURR.topics_by_module[mid]
        correct, total = db.get_accuracy(USER_ID, CURR.all_item_ids_for_module(mid))
        mods.append({
            "id": mid, "emoji": CURR.module_emoji(mid), "title": CURR.module_title(mid),
            "done_count": sum(1 for t in topics if t["id"] in done),
            "lesson_count": len(topics),
            "accuracy": round(100 * correct / total) if total else None,
            "attempts": total,
        })
    c, tot = db.get_accuracy(USER_ID, [i for mid in CURR.module_order
                                       for i in CURR.all_item_ids_for_module(mid)])
    return jsonify({
        "streak": db.get_streak(USER_ID),
        "total_done": len(done),
        "total_topics": len(CURR.ordered_topic_ids),
        "overall_accuracy": round(100 * c / tot) if tot else None,
        "total_attempts": tot,
        "modules": mods,
    })


XP_PER_LEVEL = 150


def _game_stats():
    done = db.get_completed_topic_ids(USER_ID)
    all_ids = [i for mid in CURR.module_order for i in CURR.all_item_ids_for_module(mid)]
    correct, attempts = db.get_accuracy(USER_ID, all_ids)
    xp = 10 * len(done) + 5 * correct + 2 * max(0, attempts - correct)
    level = xp // XP_PER_LEVEL + 1
    streak = db.get_streak(USER_ID)
    total_topics = len(CURR.ordered_topic_ids)

    mods = []
    for mid in CURR.module_order:
        topics = CURR.topics_by_module[mid]
        dc = sum(1 for t in topics if t["id"] in done)
        c, a = db.get_accuracy(USER_ID, CURR.all_item_ids_for_module(mid))
        comp = dc / len(topics) if topics else 0
        acc = (c / a) if a else 0
        mastery = round(100 * (0.6 * comp + 0.4 * acc))
        label = ("Mastered" if mastery >= 90 else "Proficient" if mastery >= 60
                 else "Apprentice" if mastery >= 25 else "Novice")
        mods.append({"id": mid, "emoji": CURR.module_emoji(mid), "title": CURR.module_title(mid),
                     "mastery": mastery, "label": label, "done_count": dc,
                     "lesson_count": len(topics), "accuracy": round(100 * acc) if a else None})

    defs = [
        ("first", "🌱", "First Steps", "Complete your first lesson", len(done) >= 1),
        ("ten", "📚", "Getting Serious", "Complete 10 lessons", len(done) >= 10),
        ("half", "⛰️", "Halfway There", "Complete half the course", len(done) >= total_topics / 2),
        ("all", "🎓", "Course Complete", "Complete every lesson", len(done) >= total_topics),
        ("unit", "🏅", "Unit Master", "Finish a whole unit", any(m["done_count"] == m["lesson_count"] and m["lesson_count"] for m in mods)),
        ("sharp", "🎯", "Sharpshooter", "90%+ accuracy over 20+ answers", attempts >= 20 and correct / max(1, attempts) >= 0.9),
        ("century", "💯", "Centurion", "Answer 100 questions", attempts >= 100),
        ("streak3", "🔥", "On a Roll", "3-day streak", streak >= 3),
        ("streak7", "⚡", "Week Warrior", "7-day streak", streak >= 7),
    ]
    achievements = [{"id": i, "emoji": e, "name": n, "desc": d, "earned": bool(x)} for i, e, n, d, x in defs]

    return {"xp": xp, "level": level, "xp_in_level": xp % XP_PER_LEVEL, "xp_per_level": XP_PER_LEVEL,
            "streak": streak, "total_done": len(done), "total_topics": total_topics,
            "overall_accuracy": round(100 * correct / attempts) if attempts else None,
            "earned_count": sum(1 for a in achievements if a["earned"]),
            "modules": mods, "achievements": achievements}


@app.route("/api/stats")
def api_stats():
    return jsonify(_game_stats())


@app.route("/api/drill")
def api_drill():
    conn = db.get_conn()
    rows = conn.execute(
        "SELECT item_id, item_type FROM review_items WHERE chat_id = ? AND total_count > 0 "
        "ORDER BY (CAST(correct_count AS REAL) / total_count) ASC, total_count DESC LIMIT 15",
        (USER_ID,)).fetchall()
    conn.close()
    items = []
    for r in rows:
        p = CURR.parse_item_id(r["item_id"])
        if not p:
            continue
        items.append({"item_id": r["item_id"], "item_type": r["item_type"],
                      "topic_id": p["topic"]["id"], "topic_title": p["topic"]["title"],
                      **{k: v for k, v in p.items() if k != "topic"}})
    return jsonify({"items": items, "count": len(items)})


@app.route("/api/exam/<module>")
def api_exam(module):
    if module not in CURR.topics_by_module:
        return jsonify({"error": "not found"}), 404
    pool = []
    for t in CURR.topics_by_module[module]:
        for i, q in enumerate(t.get("quiz", [])):
            pool.append({"item_id": CURR.quiz_item_id(t["id"], i), "q": q["q"], "choices": q["choices"]})
    random.shuffle(pool)
    pool = pool[:12]
    return jsonify({"module": module, "emoji": CURR.module_emoji(module),
                    "title": CURR.module_title(module), "questions": pool, "pass_pct": 80})


@app.route("/api/exam/<module>/submit", methods=["POST"])
def api_exam_submit(module):
    answers = request.get_json(force=True).get("answers", {})
    results, correct = [], 0
    for item_id, chosen in answers.items():
        parsed = CURR.parse_item_id(item_id)
        if not parsed or parsed.get("kind") != "quiz":
            continue
        ok = chosen == parsed["answer"]
        correct += 1 if ok else 0
        db.record_review_result(USER_ID, item_id, "quiz", 5 if ok else 2)
        results.append({"item_id": item_id, "correct": ok, "answer": parsed["answer"],
                        "explanation": parsed.get("explanation", "")})
    total = len(results)
    passed = db.record_exam(USER_ID, module, correct, total)
    db.record_activity(USER_ID)
    return jsonify({"score": correct, "total": total, "passed": passed, "pass_pct": 80, "results": results})


@app.route("/api/exams")
def api_exams():
    res = db.get_exam_results(USER_ID)
    mods = []
    for mid in CURR.module_order:
        r = res.get(mid)
        mods.append({"id": mid, "emoji": CURR.module_emoji(mid), "title": CURR.module_title(mid),
                     "quiz_count": sum(len(t.get("quiz", [])) for t in CURR.topics_by_module[mid]),
                     "passed": bool(r and r["passed"]),
                     "best": f"{r['score']}/{r['total']}" if r else None})
    passed_count = sum(1 for m in mods if m["passed"])
    return jsonify({"modules": mods, "passed_count": passed_count, "total_modules": len(mods),
                    "certificate_ready": passed_count == len(mods)})


@app.route("/api/interview", methods=["POST"])
def api_interview():
    if not _tutor_on():
        return jsonify({"reply": "🔑 The mock interview needs your Anthropic API key. Add "
                                 "ANTHROPIC_API_KEY to the Pi's ~/qe-trainer/.env and restart.",
                        "need_key": True})
    history = request.get_json(force=True).get("history", [])
    system = (
        "You are a senior Quality Engineering hiring manager at Tesla running a realistic interview "
        "for a QE role. Ask ONE question at a time, alternating technical (SPC, capability/Cpk, MSA/Gauge "
        "R&R, GD&T, FMEA, DOE, root-cause/8D) and behavioral. After each answer, give brief honest feedback "
        "(1-2 sentences) — strengths and what to improve — then ask the next question, getting progressively "
        "harder. Keep every turn short and conversational. If starting, greet in one line and ask question 1.")
    msgs = [{"role": "assistant" if m.get("role") == "interviewer" else "user",
             "content": m.get("text", "")} for m in history] or [{"role": "user", "content": "Let's begin."}]
    if msgs[0]["role"] == "assistant":  # Claude requires the first turn to be 'user'
        msgs.insert(0, {"role": "user", "content": "Let's begin the interview."})
    try:
        import anthropic
        resp = anthropic.Anthropic().messages.create(model=TUTOR_MODEL, max_tokens=600, system=system, messages=msgs)
        return jsonify({"reply": "".join(b.text for b in resp.content if b.type == "text").strip()})
    except Exception as e:
        return jsonify({"reply": f"Interview error: {e}"})


@app.route("/api/ask", methods=["POST"])
def api_ask():
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return jsonify({"answer": "Q&A needs an Anthropic API key in .env. "
                                  "Add ANTHROPIC_API_KEY=… and restart.", "sources": []})
    global _retriever
    try:
        if _retriever is None:
            from rag.retriever import Retriever
            _retriever = Retriever()
        import anthropic
        q = request.get_json(force=True)["question"]
        hits = _retriever.search(q, k=5)
        ctx = "\n\n".join(f"[{h['book']} p{h['page']}] {h['text']}" for h in hits)
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=os.environ.get("QE_ASK_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=700,
            system="You are a Quality Engineering tutor. Answer from the provided book "
                   "excerpts; cite the book and page. If unsure, say so.",
            messages=[{"role": "user", "content": f"Excerpts:\n{ctx}\n\nQuestion: {q}"}],
        )
        return jsonify({"answer": msg.content[0].text,
                        "sources": [{"book": h["book"], "page": h["page"]} for h in hits]})
    except Exception as e:
        return jsonify({"answer": f"Q&A error: {e}", "sources": []}), 500


# --------------------------------------------------------------------------
# AI Tutor (Anthropic) — graceful when no API key is configured
# --------------------------------------------------------------------------
TUTOR_MODEL = os.environ.get("QE_TUTOR_MODEL", "claude-opus-4-8")
SYSTEM_TUTOR = (
    "You are an expert Quality Engineering tutor coaching a learner toward a Tesla-level QE role. "
    "Be precise, use correct terminology, and teach with intuition and real manufacturing examples. "
    "When book excerpts are provided, ground your answer in them and cite the book and page. Keep it focused."
)


def _tutor_on():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _need_key():
    return {"need_key": True,
            "answer": "🔑 The AI Tutor needs your Anthropic API key. Add ANTHROPIC_API_KEY to "
                      "~/qe-trainer/.env and restart the server.",
            "feedback": "🔑 Add your Anthropic API key (ANTHROPIC_API_KEY in .env) to enable AI grading."}


def _book_context(query, k=4):
    global _retriever
    try:
        if _retriever is None:
            from rag.retriever import Retriever
            _retriever = Retriever()
        hits = _retriever.search(query, k=k)
        ctx = "\n\n".join(f"[{h['book']} p{h['page']}] {h['text']}" for h in hits)
        return ctx, [{"book": h["book"], "page": h["page"]} for h in hits]
    except Exception:
        return "", []


def _ask_claude(system, user_text, max_tokens=1024, thinking=False):
    import anthropic
    client = anthropic.Anthropic()
    kwargs = dict(model=TUTOR_MODEL, max_tokens=max_tokens, system=system,
                  messages=[{"role": "user", "content": user_text}])
    if thinking:
        kwargs["thinking"] = {"type": "adaptive"}
    msg = client.messages.create(**kwargs)
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def _topic_context(tid):
    t = CURR.topic_by_id.get(tid, {})
    return (f"Topic: {t.get('title','')}\nSummary: {t.get('summary','')}\n"
            f"Reading: {t.get('reading','')}")[:4000]


@app.route("/api/tutor/ask", methods=["POST"])
def tutor_ask():
    if not _tutor_on():
        return jsonify({**_need_key(), "sources": []})
    q = (request.get_json(force=True).get("question") or "").strip()
    if not q:
        return jsonify({"answer": "Ask me anything about quality engineering.", "sources": []})
    ctx, sources = _book_context(q)
    user = (f"Book excerpts (use if relevant, cite book+page):\n{ctx}\n\n" if ctx else "") + f"Question: {q}"
    try:
        return jsonify({"answer": _ask_claude(SYSTEM_TUTOR, user, 1024), "sources": sources})
    except Exception as e:
        return jsonify({"answer": f"Tutor error: {e}", "sources": []})


@app.route("/api/tutor/grade", methods=["POST"])
def tutor_grade():
    if not _tutor_on():
        return jsonify(_need_key())
    d = request.get_json(force=True)
    ua = (d.get("user_answer") or "").strip()
    if not ua:
        return jsonify({"feedback": "Write your answer first, then I'll grade it."})
    system = (SYSTEM_TUTOR + " You are grading the learner's free-text answer to a critical-thinking "
              "prompt. Be encouraging but rigorous: name what they got right, what's missing or wrong, "
              "and the key insight they should take away. End with a one-line verdict — 'Strong', "
              "'On the right track', or 'Needs work'. Under 180 words.")
    user = (f"Prompt: {d.get('prompt','')}\n\nReference (model) answer: {d.get('model_answer','')}\n\n"
            f"Learner's answer: {ua}\n\nGrade the learner's answer.")
    try:
        return jsonify({"feedback": _ask_claude(system, user, 1600, thinking=True)})
    except Exception as e:
        return jsonify({"feedback": f"Tutor error: {e}"})


@app.route("/api/tutor/explain", methods=["POST"])
def tutor_explain():
    if not _tutor_on():
        return jsonify(_need_key())
    d = request.get_json(force=True)
    tid, mode = d.get("topic_id", ""), d.get("mode", "simpler")
    instr = {"simpler": "Re-explain this topic more simply, as if to a smart beginner, with an analogy.",
             "example": "Give a fresh, concrete real-world manufacturing example that illustrates this topic.",
             "deeper": "Go deeper on this topic — the subtle points and common misconceptions an expert knows."}.get(mode, "Re-explain this topic.")
    try:
        return jsonify({"answer": _ask_claude(SYSTEM_TUTOR, f"{_topic_context(tid)}\n\n{instr}", 900)})
    except Exception as e:
        return jsonify({"answer": f"Tutor error: {e}"})


@app.route("/api/tutor/practice", methods=["POST"])
def tutor_practice():
    if not _tutor_on():
        return jsonify(_need_key())
    tid = request.get_json(force=True).get("topic_id", "")
    user = (f"{_topic_context(tid)}\n\nWrite ONE new application/scenario question that tests judgment "
            "on this topic (not simple recall). Then on a new line write '---ANSWER---' followed by the "
            "ideal answer with reasoning.")
    try:
        out = _ask_claude(SYSTEM_TUTOR, user, 900)
        q, _, a = out.partition("---ANSWER---")
        return jsonify({"question": q.strip(), "answer": a.strip() or "(answer not provided)"})
    except Exception as e:
        return jsonify({"question": f"Tutor error: {e}", "answer": ""})


@app.route("/api/tutor/status")
def tutor_status():
    return jsonify({"enabled": _tutor_on(), "model": TUTOR_MODEL})


# --------------------------------------------------------------------------
# Read & Master — read the real source, then prove understanding (open-ended, AI-graded)
# --------------------------------------------------------------------------
def _topic_passages(tid, k=4):
    t = CURR.topic_by_id.get(tid, {})
    query = f"{t.get('title', '')} {t.get('summary', '')}"
    global _retriever
    try:
        if _retriever is None:
            from rag.retriever import Retriever
            _retriever = Retriever()
        return [{"book": h["book"], "page": h["page"], "text": h["text"]}
                for h in _retriever.search(query, k=k)]
    except Exception:
        return []


@app.route("/api/master/<tid>")
def api_master(tid):
    t = CURR.topic_by_id.get(tid)
    if not t:
        return jsonify({"error": "not found"}), 404
    passages = _topic_passages(tid)
    out = {"id": tid, "title": t["title"], "source": t["source"], "module": t["module"],
           "passages": passages, "mastered": tid in db.get_mastered_topic_ids(USER_ID), "questions": []}
    if not _tutor_on():
        out["need_key"] = True
        return jsonify(out)
    src = "\n\n".join(f"[{p['book']} p{p['page']}] {p['text']}" for p in passages) or t.get("reading", "")
    system = ("You are a Quality Engineering examiner. Write OPEN-ENDED questions that require explaining "
              "reasoning or applying the concept to a realistic manufacturing scenario — never definition or "
              "recall lookups, and not answerable by quoting a sentence.")
    user = (f"Source material:\n{src}\n\nTopic: {t['title']}\n\nWrite exactly 3 such questions. "
            "Output ONLY the questions, one per line, numbered 1-3, no answers.")
    try:
        raw = _ask_claude(system, user, 500)
        qs = [re.sub(r"^\s*\d+[.)]\s*", "", ln).strip() for ln in raw.splitlines() if ln.strip()]
        out["questions"] = [q for q in qs if len(q) > 8][:3]
    except Exception as e:
        out["error"] = str(e)
    return jsonify(out)


@app.route("/api/master/<tid>/grade", methods=["POST"])
def api_master_grade(tid):
    if not _tutor_on():
        return jsonify(_need_key())
    t = CURR.topic_by_id.get(tid)
    if not t:
        return jsonify({"error": "not found"}), 404
    items = request.get_json(force=True).get("items", [])
    passages = _topic_passages(tid)
    src = "\n\n".join(f"[{p['book']} p{p['page']}] {p['text']}" for p in passages) or t.get("reading", "")
    results, passed_all = [], bool(items)
    for it in items:
        q, ans = it.get("question", ""), (it.get("answer") or "").strip()
        if not ans:
            results.append({"question": q, "passed": False, "feedback": "No answer given."})
            passed_all = False
            continue
        system = ("You are a strict but fair Quality Engineering examiner grading to the standard the source "
                  "material requires. Judge whether the learner's answer demonstrates the necessary understanding.")
        user = (f"Source material:\n{src}\n\nQuestion: {q}\n\nLearner's answer: {ans}\n\n"
                "Respond with EXACTLY 'PASS' or 'RETRY' on the first line, then 1-3 sentences of specific "
                "feedback — what was right and what was missing.")
        try:
            graded = _ask_claude(system, user, 600)
            lines = [ln for ln in graded.strip().splitlines() if ln.strip()]
            first = lines[0] if lines else ""
            ok = re.sub(r"[^A-Za-z]", "", first).upper().startswith("PASS")
            fb = "\n".join(lines[1:]).strip()
            if not fb:
                fb = first if not re.sub(r"[^A-Za-z]", "", first).upper() in ("PASS", "RETRY") else ""
            fb = fb or ("Solid — you covered the key reasoning." if ok
                        else "Not quite — give the specific reasoning the scenario calls for and try again.")
            results.append({"question": q, "passed": ok, "feedback": fb})
            passed_all = passed_all and ok
        except Exception as e:
            results.append({"question": q, "passed": False, "feedback": f"Grading error: {e}"})
            passed_all = False
    if passed_all:
        db.record_mastery(USER_ID, tid)
        db.record_activity(USER_ID)
    return jsonify({"results": results, "mastered": passed_all})


LIBRARY = [
    {"id": "evans-spc", "title": "SPC for Quality Improvement", "author": "James Evans", "units": "SPC · Process Variation"},
    {"id": "six-sigma", "title": "Six Sigma: A Complete Step-by-Step Guide", "author": "CSSC", "units": "Capability · MSA · DOE"},
    {"id": "statistical-engineering", "title": "Statistical Engineering: Reducing Variation", "author": "MacKay & Steiner", "units": "Process Variation"},
    {"id": "cogorno-gdt", "title": "Geometric Dimensioning & Tolerancing", "author": "Gene Cogorno", "units": "GD&T"},
    {"id": "fmea-handbook", "title": "FMEA Handbook", "author": "AIAG-VDA", "units": "FMEA"},
]


@app.route("/api/library")
def api_library():
    pdfs = STATIC / "pdfs"
    books = [{**b, "url": f"/pdfs/{b['id']}.pdf"} for b in LIBRARY if (pdfs / f"{b['id']}.pdf").exists()]
    return jsonify({"books": books})


@app.route("/api/mastery")
def api_mastery():
    m = db.get_mastered_topic_ids(USER_ID)
    mods = [{"id": mid, "emoji": CURR.module_emoji(mid), "title": CURR.module_title(mid),
             "mastered": sum(1 for t in CURR.topics_by_module[mid] if t["id"] in m),
             "total": len(CURR.topics_by_module[mid])} for mid in CURR.module_order]
    return jsonify({"mastered_ids": list(m), "total_mastered": len(m),
                    "total_topics": len(CURR.ordered_topic_ids), "modules": mods})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
