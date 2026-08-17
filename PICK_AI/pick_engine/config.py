from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models"
TOKENIZER_DIR = ROOT / "tokenizer"

for p in (DATA_DIR, MODEL_DIR, TOKENIZER_DIR):
    p.mkdir(parents=True, exist_ok=True)

@dataclass
class ModelConfig:
    vocab_size: int = 16000
    max_seq_len: int = 512
    d_model: int = 384
    n_heads: int = 6
    n_layers: int = 6
    d_ff: int = 1536
    dropout: float = 0.1
    rope_base: float = 10000.0
    tie_embeddings: bool = True

    def save(self, path: Path):
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path):
        return cls(**json.loads(path.read_text(encoding="utf-8")))
