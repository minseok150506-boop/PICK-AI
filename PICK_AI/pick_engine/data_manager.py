from __future__ import annotations
import json
import random
from pathlib import Path
from typing import Iterable

from .config import DATA_DIR

RAW = DATA_DIR / "raw"
PROCESSED = DATA_DIR / "processed"
TRAINING = DATA_DIR / "training"
VALIDATION = DATA_DIR / "validation"
KNOWLEDGE = DATA_DIR / "knowledge"
FEEDBACK = DATA_DIR / "user_feedback"

for p in (RAW, PROCESSED, TRAINING, VALIDATION, KNOWLEDGE, FEEDBACK):
    p.mkdir(parents=True, exist_ok=True)

def normalize_message(message: dict) -> dict | None:
    role = str(message.get("role") or "").strip().lower()
    content = str(message.get("content") or "").strip()
    if role not in {"system", "user", "assistant"} or not content:
        return None
    return {"role": role, "content": content}

def normalize_example(item: dict) -> dict | None:
    messages = []
    for message in item.get("messages") or []:
        clean = normalize_message(message)
        if clean:
            messages.append(clean)
    if len(messages) < 2:
        return None
    return {"messages": messages}

def read_jsonl(path: str | Path):
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                row = normalize_example(json.loads(line))
                if row:
                    rows.append(row)
            except Exception:
                continue
    return rows

def write_jsonl(path: str | Path, rows: Iterable[dict]):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

def dedupe(rows):
    seen = set()
    out = []
    for row in rows:
        key = json.dumps(row, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out

def build_dataset(
    sources: list[str | Path],
    train_path: str | Path = TRAINING / "train.jsonl",
    validation_path: str | Path = VALIDATION / "validation.jsonl",
    validation_ratio: float = 0.05,
    seed: int = 42,
):
    rows = []
    for source in sources:
        rows.extend(read_jsonl(source))
    rows = dedupe(rows)
    random.Random(seed).shuffle(rows)

    if not rows:
        write_jsonl(train_path, [])
        write_jsonl(validation_path, [])
        return {"total": 0, "train": 0, "validation": 0}

    n_val = max(1, int(len(rows) * validation_ratio)) if len(rows) >= 20 else 0
    validation = rows[:n_val]
    training = rows[n_val:]

    write_jsonl(train_path, training)
    write_jsonl(validation_path, validation)
    return {
        "total": len(rows),
        "train": len(training),
        "validation": len(validation),
    }
