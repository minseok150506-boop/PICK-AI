from __future__ import annotations
from pathlib import Path
import sentencepiece as spm

from .config import TOKENIZER_DIR

MODEL_PREFIX = TOKENIZER_DIR / "pick_spm"
MODEL_FILE = TOKENIZER_DIR / "pick_spm.model"

SPECIAL = {
    "pad": 0,
    "unk": 1,
    "bos": 2,
    "eos": 3,
}

class PickTokenizer:
    def __init__(self, model_file: str | Path = MODEL_FILE):
        self.model_file = Path(model_file)
        if not self.model_file.exists():
            raise FileNotFoundError(
                f"토크나이저가 없습니다: {self.model_file}. "
                "먼저 train_tokenizer.py를 실행하세요."
            )
        self.sp = spm.SentencePieceProcessor(model_file=str(self.model_file))

    @property
    def vocab_size(self):
        return self.sp.get_piece_size()

    def encode(self, text: str, add_bos=True, add_eos=False):
        ids = self.sp.encode(str(text), out_type=int)
        if add_bos:
            ids = [SPECIAL["bos"]] + ids
        if add_eos:
            ids = ids + [SPECIAL["eos"]]
        return ids

    def decode(self, ids):
        filtered = [int(x) for x in ids if int(x) >= 4]
        return self.sp.decode(filtered)

def train_tokenizer(
    corpus_file: str | Path,
    vocab_size: int = 16000,
    character_coverage: float = 0.9995,
):
    corpus_file = Path(corpus_file)
    if not corpus_file.exists():
        raise FileNotFoundError(corpus_file)

    spm.SentencePieceTrainer.train(
        input=str(corpus_file),
        model_prefix=str(MODEL_PREFIX),
        vocab_size=int(vocab_size),
        model_type="bpe",
        character_coverage=float(character_coverage),
        pad_id=SPECIAL["pad"],
        unk_id=SPECIAL["unk"],
        bos_id=SPECIAL["bos"],
        eos_id=SPECIAL["eos"],
        user_defined_symbols=["<|system|>", "<|user|>", "<|assistant|>", "<|memory|>", "<|tool|>"],
        input_sentence_size=2000000,
        shuffle_input_sentence=True,
        byte_fallback=True,
        normalization_rule_name="nmt_nfkc_cf",
    )
    return MODEL_FILE
