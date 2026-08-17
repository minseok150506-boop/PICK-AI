from __future__ import annotations

import re

from memory_engine import (
    get_conversation_summary,
    get_settings,
    upsert_conversation_summary,
)


def should_refresh_summary(messages: list[dict], current_summary: str) -> bool:
    if len(messages) < 10:
        return False
    # Refresh every ~8 messages after enough conversation exists.
    return len(messages) % 8 in {0, 1}


def fallback_summary(messages: list[dict], limit_chars: int = 3500) -> str:
    recent = messages[-16:]
    lines = []
    for m in recent:
        role = "사용자" if m.get("role") == "user" else "PICK"
        content = re.sub(r"\s+", " ", str(m.get("content") or "")).strip()
        if not content:
            continue
        lines.append(f"{role}: {content[:350]}")
    return "\n".join(lines)[-limit_chars:]


def build_summary_prompt(messages: list[dict], old_summary: str = "") -> str:
    recent = messages[-20:]
    transcript = "\n".join(
        f"{m.get('role')}: {str(m.get('content') or '')[:1500]}"
        for m in recent
    )
    return f"""Summarize this conversation for future memory retrieval.

Rules:
- Keep user goals, preferences, decisions, project constraints, unresolved problems, filenames, model names, and important dates.
- Do not include hidden reasoning.
- Do not invent anything.
- Keep it concise.
- If a newer user statement contradicts an older one, keep the newer statement.
- Output only the summary.

Previous summary:
{old_summary}

Recent conversation:
{transcript}
"""


def refresh_summary_if_needed(user_id, chat_id, messages, summarizer=None):
    settings = get_settings(user_id)
    if not settings["enabled"] or not settings["auto_summary"]:
        return get_conversation_summary(user_id, chat_id)

    old = get_conversation_summary(user_id, chat_id)
    if not should_refresh_summary(messages, old):
        return old

    summary = ""
    if summarizer:
        try:
            summary = str(summarizer(build_summary_prompt(messages, old)) or "").strip()
        except Exception:
            summary = ""

    if not summary:
        summary = fallback_summary(messages)

    last_id = messages[-1].get("id", 0) if messages else 0
    upsert_conversation_summary(user_id, chat_id, summary, last_id)
    return summary
