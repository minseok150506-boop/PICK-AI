from __future__ import annotations
import argparse
import json
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="PICK training JSONL")
    p.add_argument("--corpus", default="pick_engine/data/corpus.txt")
    p.add_argument("--dataset", default="pick_engine/data/train.jsonl")
    args = p.parse_args()

    inp = Path(args.input)
    corpus = Path(args.corpus)
    dataset = Path(args.dataset)
    corpus.parent.mkdir(parents=True, exist_ok=True)
    dataset.parent.mkdir(parents=True, exist_ok=True)

    corpus_lines = []
    rows = []

    with inp.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            messages = item.get("messages") or []
            clean = []
            for m in messages:
                role = str(m.get("role") or "user")
                content = str(m.get("content") or "").strip()
                if content:
                    clean.append({"role": role, "content": content})
                    corpus_lines.append(content)
            if clean:
                rows.append({"messages": clean})

    corpus.write_text("\n".join(corpus_lines), encoding="utf-8")
    with dataset.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("corpus:", corpus)
    print("dataset:", dataset)
    print("examples:", len(rows))

if __name__ == "__main__":
    main()
