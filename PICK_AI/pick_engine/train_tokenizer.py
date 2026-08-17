from __future__ import annotations
import argparse
from .tokenizer import train_tokenizer

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--corpus", default="pick_engine/data/corpus.txt")
    p.add_argument("--vocab-size", type=int, default=16000)
    args = p.parse_args()
    path = train_tokenizer(args.corpus, args.vocab_size)
    print("토크나이저 학습 완료:", path)

if __name__ == "__main__":
    main()
