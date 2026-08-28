from __future__ import annotations

import json
from database import connect, now


def init_learning_schema():
    conn = connect()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS learning_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        message_id INTEGER,
        rating INTEGER NOT NULL CHECK(rating IN (-1,1)),
        user_prompt TEXT NOT NULL DEFAULT '',
        assistant_answer TEXT NOT NULL DEFAULT '',
        note TEXT NOT NULL DEFAULT '',
        approved_for_training INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_learning_feedback_user
      ON learning_feedback(user_id, created_at DESC);

    CREATE TABLE IF NOT EXISTS training_examples (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        instruction TEXT NOT NULL,
        response TEXT NOT NULL,
        source_feedback_id INTEGER,
        language TEXT NOT NULL DEFAULT 'auto',
        approved INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(source_feedback_id) REFERENCES learning_feedback(id) ON DELETE SET NULL
    );

    CREATE INDEX IF NOT EXISTS idx_training_examples_user
      ON training_examples(user_id, approved, id);
    """)
    conn.commit()
    conn.close()


def _previous_user_prompt(chat_id: int, assistant_message_id: int | None):
    conn = connect()
    if assistant_message_id:
        row = conn.execute(
            """SELECT content FROM chat_messages
               WHERE chat_id=? AND role='user' AND id<?
               ORDER BY id DESC LIMIT 1""",
            (chat_id, assistant_message_id)
        ).fetchone()
    else:
        row = conn.execute(
            """SELECT content FROM chat_messages
               WHERE chat_id=? AND role='user'
               ORDER BY id DESC LIMIT 1""",
            (chat_id,)
        ).fetchone()
    conn.close()
    return row["content"] if row else ""


def add_feedback(user_id, chat_id, message_id, rating, assistant_answer, note=""):
    rating = 1 if int(rating) > 0 else -1
    prompt = _previous_user_prompt(chat_id, message_id)
    conn = connect()
    cur = conn.execute(
        """INSERT INTO learning_feedback(
             user_id,chat_id,message_id,rating,user_prompt,assistant_answer,note,
             approved_for_training,created_at
           ) VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            user_id, chat_id, message_id, rating,
            prompt[:12000], str(assistant_answer or "")[:24000],
            str(note or "")[:2000], 0, now()
        )
    )
    fid = cur.lastrowid
    conn.commit()
    conn.close()
    return fid


def approve_feedback(user_id, feedback_id):
    conn = connect()
    row = conn.execute(
        """SELECT * FROM learning_feedback
           WHERE id=? AND user_id=?""",
        (feedback_id, user_id)
    ).fetchone()
    if not row:
        conn.close()
        return False

    conn.execute(
        "UPDATE learning_feedback SET approved_for_training=1 WHERE id=?",
        (feedback_id,)
    )
    if row["rating"] == 1 and row["user_prompt"].strip() and row["assistant_answer"].strip():
        exists = conn.execute(
            "SELECT 1 FROM training_examples WHERE source_feedback_id=?",
            (feedback_id,)
        ).fetchone()
        if not exists:
            conn.execute(
                """INSERT INTO training_examples(
                     user_id,instruction,response,source_feedback_id,language,approved,created_at
                   ) VALUES(?,?,?,?,?,1,?)""",
                (
                    user_id,
                    row["user_prompt"],
                    row["assistant_answer"],
                    feedback_id,
                    "auto",
                    now()
                )
            )
    conn.commit()
    conn.close()
    return True


def list_feedback(user_id, limit=100):
    conn = connect()
    rows = conn.execute(
        """SELECT id,chat_id,message_id,rating,user_prompt,assistant_answer,note,
                  approved_for_training,created_at
           FROM learning_feedback WHERE user_id=?
           ORDER BY id DESC LIMIT ?""",
        (user_id, max(1, min(int(limit), 500)))
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def training_stats(user_id):
    conn = connect()
    positive = conn.execute(
        "SELECT COUNT(*) c FROM learning_feedback WHERE user_id=? AND rating=1",
        (user_id,)
    ).fetchone()["c"]
    negative = conn.execute(
        "SELECT COUNT(*) c FROM learning_feedback WHERE user_id=? AND rating=-1",
        (user_id,)
    ).fetchone()["c"]
    approved = conn.execute(
        "SELECT COUNT(*) c FROM training_examples WHERE user_id=? AND approved=1",
        (user_id,)
    ).fetchone()["c"]
    conn.close()
    return {"positive": positive, "negative": negative, "approved_examples": approved}


def export_jsonl(user_id):
    conn = connect()
    rows = conn.execute(
        """SELECT instruction,response,language FROM training_examples
           WHERE user_id=? AND approved=1 ORDER BY id""",
        (user_id,)
    ).fetchall()
    conn.close()

    lines = []
    for row in rows:
        record = {
            "messages": [
                {"role": "user", "content": row["instruction"]},
                {"role": "assistant", "content": row["response"]},
            ],
            "language": row["language"],
        }
        lines.append(json.dumps(record, ensure_ascii=False))
    return "\n".join(lines) + ("\n" if lines else "")


def _learning_tokens(text):
    import re
    return set(x.lower() for x in re.findall(
        r"[A-Za-z][A-Za-z0-9_.:+#/-]{1,}|[가-힣]{2,}", str(text or "")
    ))


def format_training_examples(user_id, query, limit=3):
    """Retrieve user-approved good-answer examples as style/task guidance."""
    conn = connect()
    rows = conn.execute(
        """SELECT instruction,response FROM training_examples
           WHERE user_id=? AND approved=1 ORDER BY id DESC LIMIT 300""",
        (user_id,)
    ).fetchall()
    conn.close()
    if not rows:
        return ""

    q = _learning_tokens(query)
    scored = []
    for row in rows:
        inst = str(row["instruction"] or "")
        tokens = _learning_tokens(inst)
        overlap = len(q & tokens)
        score = overlap / max(1, len(q | tokens)) if q else 0.0
        if score > 0 or len(rows) <= limit:
            scored.append((score, inst, str(row["response"] or "")))
    scored.sort(key=lambda x: x[0], reverse=True)
    picked = scored[:max(1, min(int(limit), 5))]
    if not picked:
        return ""

    lines = [
        "[User-approved answer examples]",
        "Use these only as examples of helpful style/approach. Do not copy errors or facts blindly.",
    ]
    for _, instruction, response in picked:
        lines.append(f"- User: {instruction[:700]}")
        lines.append(f"  Helpful answer example: {response[:1200]}")
    return "\n".join(lines)


init_learning_schema()
