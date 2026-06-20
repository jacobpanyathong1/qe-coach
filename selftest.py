"""Offline smoke test: exercises DB, spaced repetition, session builder, and
retriever without needing a Telegram token or API key. Run: python3 selftest.py
"""
import os
import tempfile

# Use a throwaway DB so we never touch real progress.
import db
db.DB_PATH = os.path.join(tempfile.gettempdir(), "qe_selftest.db")
if os.path.exists(db.DB_PATH):
    os.remove(db.DB_PATH)

import bot
from content_loader import Curriculum

CURR = bot.CURR
CHAT = 99999


def check(label, cond):
    print(("  PASS" if cond else "  FAIL") + f"  {label}")
    assert cond, label


print("1. DB init + user")
db.init_db()
db.get_or_create_user(CHAT)
check("user exists", db.get_or_create_user(CHAT)["chat_id"] == CHAT)

print("2. Curriculum loaded")
check("37 topics", len(CURR.ordered_topic_ids) == 37)
check("first module is physics", CURR.ordered_topic_ids[0].startswith("phys"))
check("parse_item_id quiz", CURR.parse_item_id("spc-01:quiz:0")["kind"] == "quiz")
check("parse_item_id flashcard", CURR.parse_item_id("gdt-01:fc:0")["kind"] == "flashcard")

print("3. next_new_topic_id follows order")
check("next is first topic", bot.next_new_topic_id(CHAT) == CURR.ordered_topic_ids[0])

print("4. Session queue (5 / 15 / 30 min)")
q5 = bot.build_session_queue(CHAT, 5)
q15 = bot.build_session_queue(CHAT, 15)
q30 = bot.build_session_queue(CHAT, 30)
check("5-min has >=1 item", len(q5) >= 1)
check("15-min has a lesson", any(s["type"] == "lesson" for s in q15))
check("30-min has 2 lessons", sum(1 for s in q30 if s["type"] == "lesson") == 2)
print(f"     queue sizes: 5min={len(q5)} 15min={len(q15)} 30min={len(q30)}")

print("5. Mark topics done -> progress advances")
for s in q15:
    if s["type"] == "lesson":
        db.mark_topic_seen(CHAT, s["topic_id"])
done = db.get_completed_topic_ids(CHAT)
check("at least 1 topic done", len(done) >= 1)
check("next topic changed", bot.next_new_topic_id(CHAT) not in done)

print("6. Spaced repetition (SM-2)")
item = "spc-01:quiz:0"
db.record_review_result(CHAT, item, "quiz", 5)  # correct
row = db.get_conn().execute("SELECT * FROM review_items WHERE item_id=?", (item,)).fetchone()
check("interval grew after correct", row["interval_days"] >= 1)
check("reps incremented", row["reps"] == 1)
db.record_review_result(CHAT, item, "quiz", 2)  # wrong -> resets
row = db.get_conn().execute("SELECT * FROM review_items WHERE item_id=?", (item,)).fetchone()
check("reps reset after wrong", row["reps"] == 0)
check("accuracy tracked (1/2)", db.get_accuracy(CHAT, [item]) == (1, 2))

print("7. Streak")
db.record_activity(CHAT)  # start_session/cmd_quiz do this in the real flow
check("streak >= 1 today", db.get_streak(CHAT) >= 1)

print("8. Rendering helpers")
check("md escapes dot", "\\." in bot.md("a.b"))
check("bar full", bot.bar(1.0) == "█" * 10)
check("bar empty", bot.bar(0.0) == "░" * 10)
lt = bot.lesson_text(CURR.ordered_topic_ids[0])
check("lesson_text non-empty", len(lt) > 50)

print("9. Retriever (TF-IDF over books)")
r = bot.get_retriever()
hits = r.search("difference between Cp and Cpk process capability", k=3)
check("retriever returns hits", len(hits) > 0)
print(f"     top hit: {hits[0]['book']} p.{hits[0]['page']} (score {hits[0]['score']:.3f})")
hits2 = r.search("bonus tolerance maximum material condition", k=3)
check("retriever finds GD&T", len(hits2) > 0)
print(f"     top hit: {hits2[0]['book']} p.{hits2[0]['page']}")

print("\nALL SELFTESTS PASSED ✅")
