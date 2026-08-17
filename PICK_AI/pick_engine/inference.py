from __future__ import annotations
from pathlib import Path
import torch
import torch.nn.functional as F

from .config import MODEL_DIR, ModelConfig
from .model import PickTransformer
from .tokenizer import PickTokenizer

def choose_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

class PickNativeEngine:
    def __init__(self, model_dir: str | Path = MODEL_DIR):
        model_dir = Path(model_dir)
        self.tokenizer = PickTokenizer()
        cfg_path = model_dir / "config.json"
        weights = model_dir / "model_latest.pt"
        if not cfg_path.exists() or not weights.exists():
            raise FileNotFoundError(
                "PICK 자체 모델이 아직 학습되지 않았습니다. "
                "train_native_ai.bat 또는 python -m pick_engine.train 을 실행하세요."
            )
        self.cfg = ModelConfig.load(cfg_path)
        self.device = choose_device()
        self.model = PickTransformer(self.cfg).to(self.device)
        state = torch.load(weights, map_location=self.device)
        self.model.load_state_dict(state)
        self.model.eval()

    @torch.inference_mode()
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 256,
        temperature: float = 0.8,
        top_p: float = 0.92,
    ):
        ids = self.tokenizer.encode(prompt, add_bos=True, add_eos=False)
        ids = ids[-self.cfg.max_seq_len:]
        x = torch.tensor([ids], dtype=torch.long, device=self.device)

        generated = []
        for _ in range(max_new_tokens):
            x_cond = x[:, -self.cfg.max_seq_len:]
            logits, _ = self.model(x_cond)
            logits = logits[:, -1, :] / max(temperature, 1e-5)

            probs = F.softmax(logits, dim=-1)
            sorted_probs, sorted_idx = torch.sort(probs, descending=True)
            cumulative = torch.cumsum(sorted_probs, dim=-1)
            mask = cumulative > top_p
            mask[..., 1:] = mask[..., :-1].clone()
            mask[..., 0] = False
            sorted_probs = sorted_probs.masked_fill(mask, 0.0)
            sorted_probs = sorted_probs / sorted_probs.sum(dim=-1, keepdim=True)

            sampled = torch.multinomial(sorted_probs, 1)
            next_id = sorted_idx.gather(-1, sampled)
            token_id = int(next_id.item())

            if token_id == 3:
                break

            generated.append(token_id)
            x = torch.cat([x, next_id], dim=1)

        return self.tokenizer.decode(generated)

    def stream(self, prompt: str, **kwargs):
        # Simple token-by-token compatible generator.
        # For the first native release, decode small increments for stability.
        text = self.generate(prompt, **kwargs)
        for chunk in text.split(" "):
            if chunk:
                yield chunk + " "
