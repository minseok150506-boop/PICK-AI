"""
Optional PICK AI LoRA fine-tuning.

This is NOT run by the normal Synology/MiniPC service.
Use it only on a machine with a supported NVIDIA CUDA GPU.

Recommended:
- Linux or WSL2
- NVIDIA CUDA GPU
- Python 3.11
- a compatible Hugging Face base model
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--dataset", default="pick_training.jsonl")
    parser.add_argument("--output", default="pick_lora_adapter")
    parser.add_argument("--epochs", type=float, default=1.0)
    args = parser.parse_args()

    try:
        import torch
        from datasets import Dataset
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            TrainingArguments,
        )
        from peft import LoraConfig
        from trl import SFTTrainer
    except Exception as exc:
        raise SystemExit(
            "학습 패키지가 없습니다. requirements-training.txt를 설치해 주세요.\n"
            f"원인: {exc}"
        )

    if not torch.cuda.is_available():
        raise SystemExit(
            "CUDA GPU를 찾지 못했습니다. 이 스크립트는 MiniPC CPU 학습용이 아닙니다."
        )

    rows = []
    with open(args.dataset, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            messages = item.get("messages") or []
            if len(messages) < 2:
                continue
            rows.append({"messages": messages})

    if len(rows) < 20:
        raise SystemExit(
            f"학습 데이터가 {len(rows)}개뿐입니다. 최소 20개 이상 검수된 예제를 권장합니다."
        )

    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=quant,
        device_map="auto",
    )

    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM",
    )

    def formatting(example):
        return tokenizer.apply_chat_template(
            example["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )

    dataset = Dataset.from_list(rows)

    train_args = TrainingArguments(
        output_dir=args.output,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        logging_steps=5,
        save_strategy="epoch",
        bf16=True,
        report_to=[],
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        peft_config=peft_config,
        formatting_func=formatting,
        args=train_args,
    )
    trainer.train()
    trainer.save_model(args.output)
    tokenizer.save_pretrained(args.output)
    print("LoRA 학습 완료:", args.output)


if __name__ == "__main__":
    main()
