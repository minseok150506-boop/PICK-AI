from __future__ import annotations
import json
from pathlib import Path
import torch
from torch.utils.data import Dataset

class ConversationDataset(Dataset):
    def __init__(self, jsonl_file, tokenizer, max_seq_len=512):
        self.rows = []
        self.tokenizer = tokenizer
        self.max_seq_len = int(max_seq_len)
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                messages = item.get("messages") or []
                if messages:
                    self.rows.append(messages)

    def __len__(self):
        return len(self.rows)

    def _format(self, messages):
        parts = []
        for m in messages:
            role = str(m.get("role", "user"))
            content = str(m.get("content", ""))
            parts.append(f"<|{role}|>\n{content}\n")
        return "".join(parts)

    def __getitem__(self, idx):
        text = self._format(self.rows[idx])
        ids = self.tokenizer.encode(text, add_bos=True, add_eos=True)
        ids = ids[: self.max_seq_len + 1]
        if len(ids) < 2:
            ids = ids + [3]
        x = torch.tensor(ids[:-1], dtype=torch.long)
        y = torch.tensor(ids[1:], dtype=torch.long)
        return x, y

def collate_batch(batch, pad_id=0):
    xs, ys = zip(*batch)
    max_len = max(len(x) for x in xs)
    bx = torch.full((len(xs), max_len), pad_id, dtype=torch.long)
    by = torch.full((len(xs), max_len), -100, dtype=torch.long)
    for i, (x, y) in enumerate(zip(xs, ys)):
        bx[i, :len(x)] = x
        by[i, :len(y)] = y
    return bx, by
