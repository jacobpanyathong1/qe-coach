"""SQLite storage + SM-2 spaced repetition for the QE training bot."""
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "progress.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    notify_time TEXT DEFAULT '08:00',
    notify_enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS progress (
    chat_id INTEGER NOT NULL,
    topic_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',  -- new | seen | done
    last_seen TEXT,
    times_reviewed INTEGER DEFAULT 0,
    PRIMARY KEY (chat_id, topic_id)
);

CREATE TABLE IF NOT EXISTS review_items (
    chat_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,       -- e.g. "gdt-01:quiz:0" or "gdt-01:fc:1"
    item_type TEXT NOT NULL,     -- 'quiz' | 'flashcard'
    ease REAL DEFAULT 2.5,
    interval_days INTEGER DEFAULT 0,
    reps INTEGER DEFAULT 0,
    due_date TEXT NOT NULL,
    last_result TEXT,
    correct_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    PRIMARY KEY (chat_id, item_id)
);

CREATE TABLE IF NOT EXISTS activity (
    chat_id INTEGER NOT NULL,
    activity_date TEXT NOT NULL,
    PRIMARY KEY (chat_id, activity_date)
);

CREATE TABLE IF NOT EXISTS exam_results (
    chat_id INTEGER NOT NULL,
    module TEXT NOT NULL,
    score INTEGER NOT NULL,
    total INTEGER NOT NULL,
    passed INTEGER NOT NULL DEFAULT 0,
    taken_at TEXT NOT NULL,
    PRIMARY KEY (chat_id, module)
);

CREATE TABLE IF NOT EXISTS mastery (
    chat_id INTEGER NOT NULL,
    topic_id TEXT NOT NULL,
    mastered_at TEXT NOT NULL,
    PRIMARY KEY (chat_id, topic_id)
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_or_create_user(chat_id: int):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (chat_id, created_at) VALUES (?, ?)",
        (chat_id, datetime.utcnow().isoformat()),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,)).fetchone()
    conn.close()
    return row


def set_notify_time(chat_id: int, hhmm: str):
    conn = get_conn()
    conn.execute("UPDATE users SET notify_time = ? WHERE chat_id = ?", (hhmm, chat_id))
    conn.commit()
    conn.close()


def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users WHERE notify_enabled = 1").fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Topic progress
# ---------------------------------------------------------------------------

def mark_topic_seen(chat_id: int, topic_id: str):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO progress (chat_id, topic_id, status, last_seen, times_reviewed)
        VALUES (?, ?, 'done', ?, 1)
        ON CONFLICT(chat_id, topic_id) DO UPDATE SET
            status = 'done',
            last_seen = excluded.last_seen,
            times_reviewed = times_reviewed + 1
        """,
        (chat_id, topic_id, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_completed_topic_ids(chat_id: int) -> set:
    conn = get_conn()
    rows = conn.execute(
        "SELECT topic_id FROM progress WHERE chat_id = ? AND status = 'done'",
        (chat_id,),
    ).fetchall()
    conn.close()
    return {r["topic_id"] for r in rows}


# ---------------------------------------------------------------------------
# Spaced repetition (SM-2)
# ---------------------------------------------------------------------------

def ensure_review_item(chat_id: int, item_id: str, item_type: str):
    conn = get_conn()
    conn.execute(
        """
        INSERT OR IGNORE INTO review_items (chat_id, item_id, item_type, due_date)
        VALUES (?, ?, ?, ?)
        """,
        (chat_id, item_id, item_type, date.today().isoformat()),
    )
    conn.commit()
    conn.close()


def get_due_items(chat_id: int, item_type: str = None, limit: int = 5):
    """Return review items due today or earlier, oldest-due first."""
    conn = get_conn()
    today = date.today().isoformat()
    if item_type:
        rows = conn.execute(
            """
            SELECT * FROM review_items
            WHERE chat_id = ? AND item_type = ? AND due_date <= ?
            ORDER BY due_date ASC LIMIT ?
            """,
            (chat_id, item_type, today, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM review_items
            WHERE chat_id = ? AND due_date <= ?
            ORDER BY due_date ASC LIMIT ?
            """,
            (chat_id, today, limit),
        ).fetchall()
    conn.close()
    return rows


def record_review_result(chat_id: int, item_id: str, item_type: str, quality: int):
    """Update SM-2 state. quality: 0-5 (5 = perfect recall, <3 = fail)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM review_items WHERE chat_id = ? AND item_id = ?",
        (chat_id, item_id),
    ).fetchone()

    if row is None:
        ease, interval, reps = 2.5, 0, 0
    else:
        ease, interval, reps = row["ease"], row["interval_days"], row["reps"]

    if quality < 3:
        interval = 1
        ease = max(1.3, ease - 0.2)
        reps = 0
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ease)
        ease = max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        reps += 1

    due = (date.today() + timedelta(days=interval)).isoformat()
    correct = 1 if quality >= 3 else 0

    conn.execute(
        """
        INSERT INTO review_items
            (chat_id, item_id, item_type, ease, interval_days, reps, due_date, last_result, correct_count, total_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(chat_id, item_id) DO UPDATE SET
            ease = ?,
            interval_days = ?,
            reps = ?,
            due_date = ?,
            last_result = ?,
            correct_count = correct_count + ?,
            total_count = total_count + 1
        """,
        (
            chat_id, item_id, item_type, ease, interval, reps, due, "correct" if correct else "incorrect", correct,
            ease, interval, reps, due, "correct" if correct else "incorrect", correct,
        ),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Activity / streaks
# ---------------------------------------------------------------------------

def record_activity(chat_id: int):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO activity (chat_id, activity_date) VALUES (?, ?)",
        (chat_id, date.today().isoformat()),
    )
    conn.commit()
    conn.close()


def get_streak(chat_id: int) -> int:
    conn = get_conn()
    rows = conn.execute(
        "SELECT activity_date FROM activity WHERE chat_id = ? ORDER BY activity_date DESC",
        (chat_id,),
    ).fetchall()
    conn.close()
    dates = {datetime.fromisoformat(r["activity_date"]).date() for r in rows}
    streak = 0
    cursor = date.today()
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


# ---------------------------------------------------------------------------
# Accuracy summary (for dashboard)
# ---------------------------------------------------------------------------

def get_accuracy(chat_id: int, item_ids: list) -> tuple:
    """Return (correct_total, attempts_total) across given item_ids."""
    if not item_ids:
        return (0, 0)
    conn = get_conn()
    placeholders = ",".join("?" * len(item_ids))
    rows = conn.execute(
        f"SELECT correct_count, total_count FROM review_items "
        f"WHERE chat_id = ? AND item_id IN ({placeholders})",
        (chat_id, *item_ids),
    ).fetchall()
    conn.close()
    correct = sum(r["correct_count"] for r in rows)
    total = sum(r["total_count"] for r in rows)
    return (correct, total)


# ---------------------------------------------------------------------------
# Module exams
# ---------------------------------------------------------------------------

def record_exam(chat_id: int, module: str, score: int, total: int, pass_pct: int = 80) -> bool:
    """Store an exam result; 'passed' is sticky (once passed, stays passed). Returns passed."""
    passed = 1 if (total and (100 * score / total) >= pass_pct) else 0
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO exam_results (chat_id, module, score, total, passed, taken_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(chat_id, module) DO UPDATE SET
            score = excluded.score,
            total = excluded.total,
            passed = MAX(exam_results.passed, excluded.passed),
            taken_at = excluded.taken_at
        """,
        (chat_id, module, score, total, passed, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()
    return bool(passed)


def get_exam_results(chat_id: int) -> dict:
    conn = get_conn()
    rows = conn.execute(
        "SELECT module, score, total, passed FROM exam_results WHERE chat_id = ?", (chat_id,)
    ).fetchall()
    conn.close()
    return {r["module"]: {"score": r["score"], "total": r["total"], "passed": bool(r["passed"])}
            for r in rows}


# ---------------------------------------------------------------------------
# Read & Master (open-ended, AI-graded mastery)
# ---------------------------------------------------------------------------

def record_mastery(chat_id: int, topic_id: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO mastery (chat_id, topic_id, mastered_at) VALUES (?, ?, ?)",
        (chat_id, topic_id, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_mastered_topic_ids(chat_id: int) -> set:
    conn = get_conn()
    rows = conn.execute("SELECT topic_id FROM mastery WHERE chat_id = ?", (chat_id,)).fetchall()
    conn.close()
    return {r["topic_id"] for r in rows}
