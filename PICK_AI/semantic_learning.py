from __future__ import annotations

import json
import math
from pathlib import Path

from config import DATA_DIR
from memory_store import list_memories

INDEX_PATH = DATA_DIR / "semantic_memory.json"


def _tokenize(text: str):
    # Dependency-free fallback semantic-ish retrieval.
    # Optional sentence-transformers index can be added later without breaking PICK.
    import re
    return [x.lower() for x in re.findall(r"[\w가-힣]{2,}", str(text or ""))]


def rebuild_user_index(user_id: int):
    memories = list_memories(user_id, 500)
    docs = []
    for m in memories:
        tokens = _tokenize(m["content"])
        docs.append({
            "id": m["id"],
            "user_id": user_id,
            "content": m["content"],
            "tokens": tokens,
        })

    all_data = {}
    if INDEX_PATH.exists():
        try:
            all_data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            all_data = {}

    all_data[str(user_id)] = docs
    INDEX_PATH.write_text(json.dumps(all_data, ensure_ascii=False), encoding="utf-8")
    return len(docs)


def retrieve(user_id: int, query: str, limit: int = 6):
    if not INDEX_PATH.exists():
        rebuild_user_index(user_id)
    try:
        all_data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        rebuild_user_index(user_id)
        all_data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))

    docs = all_data.get(str(user_id), [])
    if not docs:
        return []

    q = set(_tokenize(query))
    if not q:
        return docs[:limit]

    scored = []
    for d in docs:
        t = set(d.get("tokens") or [])
        overlap = len(q & t)
        denom = math.sqrt(max(1, len(q)) * max(1, len(t)))
        score = overlap / denom
        if score > 0:
            scored.append((score, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:limit]]
