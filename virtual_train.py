
import argparse
import json
import math
import random
import time
from pathlib import Path

def fake_loss(step, total_steps, start=4.5, end=0.9):
    progress = step / max(total_steps, 1)
    smooth = 1 - math.exp(-4 * progress)
    noise = random.uniform(-0.05, 0.05)
    return max(end, start - (start - end) * smooth + noise)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--interval", type=int, default=100)
    parser.add_argument("--sleep", type=float, default=0.005)
    parser.add_argument("--out-dir", default="models/virtual_auto")
    args = parser.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    log = out / "virtual_train_log.jsonl"

    if log.exists():
        log.unlink()

    for step in range(args.steps + 1):
        if step % args.interval == 0 or step == args.steps:
            row = {
                "step": step,
                "percent": int(step / max(args.steps, 1) * 100),
                "train_loss": round(fake_loss(step, args.steps), 4),
                "val_loss": round(fake_loss(step, args.steps, 4.8, 1.15), 4),
            }
            print(row)
            with log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\\n")
        if args.sleep:
            time.sleep(args.sleep)

    (out / "virtual_training_report.txt").write_text("가상 학습 완료", encoding="utf-8")

if __name__ == "__main__":
    main()
