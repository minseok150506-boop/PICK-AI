from __future__ import annotations
import argparse
import json
import math
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from .config import ModelConfig, MODEL_DIR
from .dataset import ConversationDataset, collate_batch
from .model import PickTransformer
from .tokenizer import PickTokenizer

def choose_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

def save_checkpoint(model, optimizer, cfg, step, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "config": cfg.__dict__,
        "step": step,
    }, out_dir / f"checkpoint_{step}.pt")
    torch.save(model.state_dict(), out_dir / "model_latest.pt")
    cfg.save(out_dir / "config.json")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True)
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--grad-accum", type=int, default=8)
    p.add_argument("--max-seq-len", type=int, default=512)
    p.add_argument("--d-model", type=int, default=384)
    p.add_argument("--layers", type=int, default=6)
    p.add_argument("--heads", type=int, default=6)
    p.add_argument("--ff", type=int, default=1536)
    p.add_argument("--save-every", type=int, default=200)
    args = p.parse_args()

    tokenizer = PickTokenizer()
    cfg = ModelConfig(
        vocab_size=tokenizer.vocab_size,
        max_seq_len=args.max_seq_len,
        d_model=args.d_model,
        n_layers=args.layers,
        n_heads=args.heads,
        d_ff=args.ff,
    )

    device = choose_device()
    print("device:", device)

    ds = ConversationDataset(args.dataset, tokenizer, cfg.max_seq_len)
    if len(ds) < 20:
        raise SystemExit("학습 데이터가 너무 적습니다. 최소 20개 이상을 권장합니다.")

    dl = DataLoader(
        ds,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=collate_batch,
        num_workers=0,
    )

    model = PickTransformer(cfg).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.1)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    total_steps = max(1, len(dl) * args.epochs)
    step = 0
    model.train()

    for epoch in range(args.epochs):
        for x, y in dl:
            x, y = x.to(device), y.to(device)
            with torch.autocast(
                device_type=device.type,
                dtype=torch.bfloat16 if device.type == "cuda" else torch.float32,
                enabled=device.type == "cuda",
            ):
                _, loss = model(x, y)
                loss = loss / args.grad_accum

            scaler.scale(loss).backward()

            if (step + 1) % args.grad_accum == 0:
                scaler.unscale_(optim)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optim)
                scaler.update()
                optim.zero_grad(set_to_none=True)

            step += 1
            if step % 10 == 0:
                print(f"epoch={epoch+1} step={step}/{total_steps} loss={loss.item()*args.grad_accum:.4f}")

            if step % args.save_every == 0:
                save_checkpoint(model, optim, cfg, step, MODEL_DIR)

    save_checkpoint(model, optim, cfg, step, MODEL_DIR)
    print("학습 완료:", MODEL_DIR)

if __name__ == "__main__":
    main()
