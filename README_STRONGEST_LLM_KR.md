
# PICK 최강 LLM 모드

이 버전은 PICK이 더 강한 Ollama 모델을 우선 사용하도록 설정한 버전입니다.

## 권장 실행 순서

1. 강력 모델 설치

```powershell
scripts\INSTALL_STRONGEST_MODEL.bat
```

또는 직접:

```powershell
ollama pull qwen2.5:32b
```

2. 실행

```powershell
scripts\START_STRONGEST_LLM.bat
```

## PC가 느리거나 메모리가 부족하면

```powershell
scripts\INSTALL_STRONG_MODEL_14B.bat
scripts\START_STRONG_14B.bat
```

## 모델 우선순위

1. qwen2.5:32b
2. qwen2.5:14b
3. llama3

주의:
32B 모델은 무겁습니다. 실행이 느리거나 멈추면 14B 모드를 쓰는 것이 현실적입니다.
