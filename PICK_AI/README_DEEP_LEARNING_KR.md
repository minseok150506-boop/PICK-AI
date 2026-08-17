# PICK AI 딥러닝 / 학습 시스템

## 지금 MiniPC에서 동작하는 학습

PICK은 사용자의 원본 대화를 무조건 자동 재학습하지 않습니다.

대신:
1. 답변 👍 / 👎 평가
2. 좋은 답변을 사용자가 학습 데이터로 승인
3. 승인된 예제만 별도 DB에 저장
4. JSONL 학습 데이터로 내보내기
5. 장기 기억 인덱스를 이용해 다음 답변에 반영

이 방식은 MiniPC에서도 바로 사용할 수 있습니다.

## 왜 5800H에서 8B를 직접 학습하지 않나요?

Ryzen 7 5800H + 32GB RAM의 CPU/iGPU 환경은
7B~8B LLM의 LoRA/QLoRA 학습 용도로는 매우 느립니다.

따라서:
- MiniPC: 추론, 데이터 수집, RAG, 평가
- 별도 NVIDIA GPU PC: 실제 미세조정
으로 분리했습니다.

## 실제 LoRA 딥러닝

학습 센터에서:
`학습 데이터 JSONL 내보내기`

파일명:
`pick_training.jsonl`

NVIDIA GPU PC에서:

```bash
pip install -r requirements-training.txt
python TRAIN_LORA_GPU.py --dataset pick_training.jsonl
```

기본 모델:
`Qwen/Qwen2.5-7B-Instruct`

## 최소 학습 자료

코드에서 20개 미만이면 학습을 중단하도록 했습니다.
실제로는 수백~수천 개의 검수된 고품질 예제가 더 좋습니다.

## 자동 학습 정책

PICK은 👍를 눌렀다고 즉시 모델 가중치를 변경하지 않습니다.
반드시 사용자의 학습 데이터 승인 단계를 거칩니다.

이유:
- 잘못된 답변의 자기증폭 방지
- 개인정보가 무단 학습되는 문제 방지
- 학습 데이터 품질 유지
- 사용자가 무엇을 학습시키는지 확인 가능

## 코딩 학습

코딩용 예제를 많이 승인해서 데이터셋을 만들고,
`qwen2.5-coder` 계열 기본 모델을 지정해 LoRA 학습하는 것도 가능합니다.

예:

```bash
python TRAIN_LORA_GPU.py \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --dataset pick_training.jsonl \
  --output pick_coder_lora
```
