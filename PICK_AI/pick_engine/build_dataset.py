from __future__ import annotations
import argparse
from pathlib import Path
from .config import DATA_DIR
from .data_manager import build_dataset

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", action="append", default=[])
    p.add_argument("--validation-ratio", type=float, default=0.05)
    args = p.parse_args()

    sources = [Path(x) for x in args.source]
    if not sources:
        defaults = [
            DATA_DIR / "user_feedback" / "approved_feedback.jsonl",
            DATA_DIR / "processed" / "conversations.jsonl",
        ]
        sources = [x for x in defaults if x.exists()]

    result = build_dataset(
        sources,
        validation_ratio=args.validation_ratio,
    )
    print("PICK dataset:", result)

if __name__ == "__main__":
    main()
