from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

from database import connect, now

MEMORY_KINDS = {
    "profile",       # stable personal facts/preferences
    "preference",    # likes/dislikes/style preferences
    "project",       # project-specific facts/constraints
    "decision",      # decisions already made
    "task",          # ongoing tasks / TODO
    "fact",          # useful factual memory
    "summary",       # compressed conversation summary
    "correction",    # user correction / newest truth
}

SENSITIVE_PATTERNS = [
    r"\b\d{6}-\d{7}\b",                     # Korean resident number-like
    r"\b(?:\d[ -]*?){13,19}\b",             # card-like long numbers
    r"(?i)\bpassword\b\s*[:=]",
    r"(?i)\bsecret\b\s*[:=]",
    r"(?i)\bapi[_ -]?key\b\s*[:=]",
    r"(?i)\btoken\b\s*[:=]",
]


@dataclass
class MemoryRecord:
    id: int
    user_id: int
    kind: str
    title: str
    content: str
    importance: int
    confidence: float
    pinned: bool
    source_chat_id: int | None
    created_at: str
    updated_at: str
    last_used_at: str | None
    use_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def init_schema():
    conn = connect()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS memory_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        kind TEXT NOT NULL,
        title TEXT NOT NULL DEFAULT '',
        content TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        importance INTEGER NOT NULL DEFAULT 3,
        confidence REAL NOT NULL DEFAULT 1.0,
        pinned INTEGER NOT NULL DEFAULT 0,
        source_chat_id INTEGER,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_used_at TEXT,
        use_count INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(source_chat_id) REFERENCES chats(id) ON DELETE SET NULL
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_user_hash
      ON memory_items(user_id, content_hash);

    CREATE INDEX IF NOT EXISTS idx_memory_user_kind
      ON memory_items(user_id, kind, importance DESC);

    CREATE INDEX IF NOT EXISTS idx_memory_user_updated
      ON memory_items(user_id, updated_at DESC);

    CREATE TABLE IF NOT EXISTS conversation_summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        summary TEXT NOT NULL,
        last_message_id INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, chat_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS memory_settings (
        user_id INTEGER PRIMARY KEY,
        enabled INTEGER NOT NULL DEFAULT 1,
        auto_extract INTEGER NOT NULL DEFAULT 1,
        auto_summary INTEGER NOT NULL DEFAULT 1,
        max_context_items INTEGER NOT NULL DEFAULT 8,
        remember_preferences INTEGER NOT NULL DEFAULT 1,
        remember_projects INTEGER NOT NULL DEFAULT 1,
        remember_decisions INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()


def _hash(content: str) -> str:
    normalized = re.sub(r"\s+", " ", str(content or "")).strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _safe_to_remember(text: str) -> bool:
    value = str(text or "")
    if len(value.strip()) < 4:
        return False
    return not any(re.search(p, value) for p in SENSITIVE_PATTERNS)


def get_settings(user_id: int) -> dict[str, Any]:
    conn = connect()
    row = conn.execute(
        "SELECT * FROM memory_settings WHERE user_id=?",
        (user_id,)
    ).fetchone()
    if not row:
        conn.execute(
            """INSERT INTO memory_settings(
                 user_id,enabled,auto_extract,auto_summary,max_context_items,
                 remember_preferences,remember_projects,remember_decisions,updated_at
               ) VALUES(?,1,1,1,12,1,1,1,?)""",
            (user_id, now())
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM memory_settings WHERE user_id=?",
            (user_id,)
        ).fetchone()
    conn.close()
    return dict(row)


def update_settings(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    current = get_settings(user_id)
    fields = {
        "enabled": 1 if payload.get("enabled", current["enabled"]) else 0,
        "auto_extract": 1 if payload.get("auto_extract", current["auto_extract"]) else 0,
        "auto_summary": 1 if payload.get("auto_summary", current["auto_summary"]) else 0,
        "max_context_items": max(1, min(int(payload.get("max_context_items", current["max_context_items"])), 30)),
        "remember_preferences": 1 if payload.get("remember_preferences", current["remember_preferences"]) else 0,
        "remember_projects": 1 if payload.get("remember_projects", current["remember_projects"]) else 0,
        "remember_decisions": 1 if payload.get("remember_decisions", current["remember_decisions"]) else 0,
    }

    conn = connect()
    conn.execute(
        """UPDATE memory_settings SET
             enabled=?,auto_extract=?,auto_summary=?,max_context_items=?,
             remember_preferences=?,remember_projects=?,remember_decisions=?,updated_at=?
           WHERE user_id=?""",
        (
            fields["enabled"], fields["auto_extract"], fields["auto_summary"],
            fields["max_context_items"], fields["remember_preferences"],
            fields["remember_projects"], fields["remember_decisions"],
            now(), user_id
        )
    )
    conn.commit()
    conn.close()
    return get_settings(user_id)


def add_memory(
    user_id: int,
    content: str,
    kind: str = "fact",
    title: str = "",
    importance: int = 3,
    confidence: float = 1.0,
    pinned: bool = False,
    source_chat_id: int | None = None,
):
    content = re.sub(r"\s+", " ", str(content or "")).strip()
    if not content:
        raise ValueError("기억할 내용이 없습니다.")
    if not _safe_to_remember(content):
        raise ValueError("민감하거나 저장하기 부적절한 정보는 자동 기억하지 않습니다.")
    if kind not in MEMORY_KINDS:
        kind = "fact"

    h = _hash(content)
    conn = connect()
    existing = conn.execute(
        "SELECT id FROM memory_items WHERE user_id=? AND content_hash=?",
        (user_id, h)
    ).fetchone()

    if existing:
        conn.execute(
            """UPDATE memory_items SET
                 kind=?,title=?,importance=?,confidence=?,pinned=?,
                 source_chat_id=COALESCE(?,source_chat_id),updated_at=?
               WHERE id=?""",
            (
                kind, str(title or "")[:160],
                max(1, min(int(importance), 5)),
                max(0.0, min(float(confidence), 1.0)),
                1 if pinned else 0,
                source_chat_id, now(), existing["id"]
            )
        )
        memory_id = existing["id"]
    else:
        cur = conn.execute(
            """INSERT INTO memory_items(
                 user_id,kind,title,content,content_hash,importance,confidence,pinned,
                 source_chat_id,created_at,updated_at,last_used_at,use_count
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL,0)""",
            (
                user_id, kind, str(title or "")[:160], content[:6000], h,
                max(1, min(int(importance), 5)),
                max(0.0, min(float(confidence), 1.0)),
                1 if pinned else 0, source_chat_id, now(), now()
            )
        )
        memory_id = cur.lastrowid

    conn.commit()
    conn.close()
    return memory_id


def list_memories(user_id: int, limit: int = 200) -> list[dict[str, Any]]:
    conn = connect()
    rows = conn.execute(
        """SELECT id,user_id,kind,title,content,importance,confidence,pinned,
                  source_chat_id,created_at,updated_at,last_used_at,use_count
           FROM memory_items
           WHERE user_id=?
           ORDER BY pinned DESC, importance DESC, datetime(updated_at) DESC
           LIMIT ?""",
        (user_id, max(1, min(int(limit), 1000)))
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_memory(user_id: int, memory_id: int) -> bool:
    conn = connect()
    cur = conn.execute(
        "DELETE FROM memory_items WHERE id=? AND user_id=?",
        (memory_id, user_id)
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def pin_memory(user_id: int, memory_id: int, pinned: bool) -> bool:
    conn = connect()
    cur = conn.execute(
        "UPDATE memory_items SET pinned=?,updated_at=? WHERE id=? AND user_id=?",
        (1 if pinned else 0, now(), memory_id, user_id)
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def _tokens(text: str) -> set[str]:
    return set(
        x.lower()
        for x in re.findall(r"[A-Za-z][A-Za-z0-9_.:+#/-]{1,}|[가-힣]{2,}|[\u4e00-\u9fff]{2,}|[\u3040-\u30ff]{2,}", str(text or ""))
    )


def _score(memory: dict[str, Any], query_tokens: set[str]) -> float:
    mt = _tokens(memory["content"] + " " + (memory.get("title") or ""))
    overlap = len(mt & query_tokens)
    lexical = overlap / max(1, math.sqrt(len(mt) * max(1, len(query_tokens))))

    importance = float(memory["importance"]) / 5.0
    confidence = float(memory["confidence"])
    pinned = 0.35 if memory["pinned"] else 0.0
    correction = 0.55 if memory.get("kind") == "correction" else 0.0
    usage = min(math.log1p(int(memory["use_count"])) / 5.0, 0.25)

    return lexical * 2.2 + importance * 0.45 + confidence * 0.25 + pinned + correction + usage


def retrieve_memories(user_id: int, query: str, limit: int | None = None) -> list[dict[str, Any]]:
    settings = get_settings(user_id)
    if not settings["enabled"]:
        return []

    if limit is None:
        limit = settings["max_context_items"]

    rows = list_memories(user_id, 500)
    q = _tokens(query)
    if not rows:
        return []

    scored = [(_score(m, q), m) for m in rows]
    scored.sort(key=lambda x: x[0], reverse=True)

    selected = [m for score, m in scored if score >= 0.35][:limit]

    if selected:
        conn = connect()
        for m in selected:
            conn.execute(
                """UPDATE memory_items
                   SET use_count=use_count+1,last_used_at=?
                   WHERE id=? AND user_id=?""",
                (now(), m["id"], user_id)
            )
        conn.commit()
        conn.close()

    return selected


def format_memory_context(user_id: int, query: str) -> str:
    rows = retrieve_memories(user_id, query)
    if not rows:
        return ""

    lines = [
        "[Relevant user memory]",
        "Use these memories only when relevant. They may be outdated; current user statements override them.",
    ]
    for m in rows:
        kind = m["kind"]
        title = f" ({m['title']})" if m.get("title") else ""
        lines.append(f"- [{kind}]{title} {m['content']}")
    return "\n".join(lines)


def auto_extract_candidates(user_text: str) -> list[dict[str, Any]]:
    """Run on every user turn and keep only useful, non-sensitive long-term signals."""
    text = re.sub(r"\s+", " ", str(user_text or "")).strip()
    if not _safe_to_remember(text):
        return []

    out: list[dict[str, Any]] = []
    lowered = text.lower()

    def add(kind: str, title: str, importance: int, confidence: float, limit: int = 1200):
        item = {
            "kind": kind,
            "title": title,
            "content": text[:limit],
            "importance": importance,
            "confidence": confidence,
        }
        if not any(x["kind"] == kind and x["content"] == item["content"] for x in out):
            out.append(item)

    correction_hints = (
        "아니야", "아니에요", "그게 아니라", "그건 아니", "틀렸", "잘못됐",
        "정정", "바꿀게", "바꿔줘", "이제부터", "앞으로는", "대신 ",
    )
    if any(h in lowered for h in correction_hints):
        add("correction", "사용자 최신 정정", 5, 0.96)

    preference_patterns = [
        r"(?:나는|저는|내가|제가)\s+(.{2,100}?)\s*(?:좋아해|좋아합니다|선호해|선호합니다|원해|원합니다)",
        r"(?:나는|저는|내가|제가)\s+(.{2,100}?)\s*(?:싫어해|싫어합니다|원하지 않아|원하지 않습니다)",
        r"(?:답변은|말투는|스타일은|설명은|언어는)\s+(.{2,140})",
        r"(?:항상|앞으로)\s+(.{2,160})",
    ]
    if any(re.search(p, text, re.I) for p in preference_patterns):
        add("preference", "사용자 선호", 4, 0.86, 900)

    project_patterns = [
        r"(?:프로젝트|서비스|앱|게임|AI|봇).{0,35}(?:이름|구조|기능|목표|색상|서버|배포|모델|설정|주소|도메인)",
        r"(?:PICK|하연 AI|윤하연 AI|Ollama|Render|GitHub|Cloudflare|qwen)\b",
    ]
    if any(re.search(p, text, re.I) for p in project_patterns):
        add("project", "프로젝트 정보", 4, 0.80, 1400)

    decision_patterns = [
        r"(?:그걸로|이걸로|이 방식으로|그렇게|이대로)\s*(?:하자|해줘|해 줘|진행|결정|가자)",
        r"(?:최종|결정|확정|채택).{0,60}",
    ]
    if any(re.search(p, text, re.I) for p in decision_patterns):
        add("decision", "사용자 결정", 4, 0.84, 1000)

    explicit_memory = (
        "기억해", "기억해줘", "기억해 줘", "잊지마", "잊지 마",
        "꼭 기억", "저장해둬", "저장해 둬",
    )
    if any(h in lowered for h in explicit_memory):
        add("fact", "사용자가 기억을 요청한 정보", 5, 0.97, 1500)

    return out


def maybe_auto_store(user_id: int, chat_id: int, user_text: str) -> list[int]:
    settings = get_settings(user_id)
    if not settings["enabled"] or not settings["auto_extract"]:
        return []

    saved = []
    for item in auto_extract_candidates(user_text):
        if item["kind"] == "preference" and not settings["remember_preferences"]:
            continue
        if item["kind"] == "project" and not settings["remember_projects"]:
            continue
        if item["kind"] == "decision" and not settings["remember_decisions"]:
            continue
        try:
            saved.append(add_memory(
                user_id=user_id,
                content=item["content"],
                kind=item["kind"],
                title=item["title"],
                importance=item["importance"],
                confidence=item["confidence"],
                source_chat_id=chat_id,
            ))
        except Exception:
            pass
    return saved


def upsert_conversation_summary(user_id: int, chat_id: int, summary: str, last_message_id: int):
    summary = str(summary or "").strip()
    if not summary:
        return
    conn = connect()
    conn.execute(
        """INSERT INTO conversation_summaries(
             user_id,chat_id,summary,last_message_id,created_at,updated_at
           ) VALUES(?,?,?,?,?,?)
           ON CONFLICT(user_id,chat_id) DO UPDATE SET
             summary=excluded.summary,
             last_message_id=excluded.last_message_id,
             updated_at=excluded.updated_at""",
        (user_id, chat_id, summary[:8000], int(last_message_id or 0), now(), now())
    )
    conn.commit()
    conn.close()


def get_conversation_summary(user_id: int, chat_id: int) -> str:
    conn = connect()
    row = conn.execute(
        "SELECT summary FROM conversation_summaries WHERE user_id=? AND chat_id=?",
        (user_id, chat_id)
    ).fetchone()
    conn.close()
    return row["summary"] if row else ""


def memory_stats(user_id: int) -> dict[str, Any]:
    conn = connect()
    total = conn.execute(
        "SELECT COUNT(*) c FROM memory_items WHERE user_id=?",
        (user_id,)
    ).fetchone()["c"]
    pinned = conn.execute(
        "SELECT COUNT(*) c FROM memory_items WHERE user_id=? AND pinned=1",
        (user_id,)
    ).fetchone()["c"]
    kinds = conn.execute(
        "SELECT kind,COUNT(*) c FROM memory_items WHERE user_id=? GROUP BY kind",
        (user_id,)
    ).fetchall()
    summaries = conn.execute(
        "SELECT COUNT(*) c FROM conversation_summaries WHERE user_id=?",
        (user_id,)
    ).fetchone()["c"]
    conn.close()
    return {
        "total": total,
        "pinned": pinned,
        "summaries": summaries,
        "by_kind": {r["kind"]: r["c"] for r in kinds},
    }


def export_all(user_id: int) -> dict[str, Any]:
    return {
        "memories": list_memories(user_id, 1000),
        "settings": get_settings(user_id),
        "stats": memory_stats(user_id),
    }


init_schema()
