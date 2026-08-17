# PICK 자체 AI 엔진

이 버전은 Ollama만 호출하는 구조에서 한 단계 더 나아가
PICK 자체 Transformer 언어모델을 직접 학습하고 실행할 수 있는 엔진을 포함합니다.

## 구조

PICK 웹(Synology)
→ PICK AI Provider Router
→ PICK Native Engine (MiniPC, 포트 11500)
→ 직접 학습한 PICK Transformer

Ollama는 필요하면 비상용 fallback으로 남길 수 있습니다.

## 자체 구현된 부분

- SentencePiece BPE 토크나이저
- Decoder-only Transformer
- RMSNorm
- Rotary Position Embedding(RoPE)
- Causal Self Attention
- PyTorch SDPA
- SwiGLU FFN
- 임베딩/LM Head weight tying
- JSONL 대화 데이터셋
- AdamW 학습
- Gradient clipping
- Gradient accumulation
- 체크포인트 저장
- Top-p / temperature 추론
- 자체 HTTP 추론 서버
- PICK 웹용 Native Engine API

즉 단순히 Ollama 모델 이름만 바꾸는 것이 아닙니다.
PICK 이름으로 직접 학습할 수 있는 별도 모델 코드가 들어 있습니다.

## 처음 설치

Windows MiniPC:

1. `INSTALL_NATIVE_ENGINE.bat`
2. PICK 학습 센터에서 `pick_training.jsonl` 내보내기
3. 프로젝트 최상위에 `pick_training.jsonl` 넣기
4. `TRAIN_NATIVE_AI.bat`
5. 학습 완료 후 `START_NATIVE_ENGINE.bat`

## 중요한 현실적 제한

기본 모델은 약 384 hidden / 6 layers 규모의 작은 Transformer입니다.
ChatGPT급 모델을 집의 CPU MiniPC에서 처음부터 학습하는 것은 현실적으로 불가능합니다.

이 엔진의 목적은:
- PICK 자체 모델 구조 확보
- 직접 데이터 수집
- 직접 토크나이저 학습
- 직접 pretraining/SFT 실험
- 향후 NVIDIA GPU 서버로 확장
입니다.

GPU가 생기면 config에서 d_model, layers, heads, sequence length를 키워 더 큰 모델로 확장할 수 있습니다.

## 권장 운영

현재:
- PICK Native Engine: 실험/전용 응답/자체 학습
- Ollama: 고성능 보조 및 fallback

향후 GPU 서버:
- PICK Native Engine을 주력으로 전환
- 자체 pretraining corpus 확대
- supervised fine-tuning
- preference optimization
- 평가셋/회귀 테스트
- 양자화/고속 serving
으로 발전시키는 구조를 권장합니다.

## 포트

PICK Native Engine 기본:
`11500`

MiniPC의 11500을 인터넷에 직접 포트포워딩하지 마세요.
Synology와 MiniPC 내부 LAN에서만 접근하는 것을 권장합니다.
