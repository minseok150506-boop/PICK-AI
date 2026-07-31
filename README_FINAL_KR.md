# PICK PERFECT FINAL

이 버전은 지금까지 만든 PICK 기능을 하나로 묶은 최종 통합판입니다.

## 포함 기능

- 한국어 답변 강화
- 영어 섞임 방지
- ChatGPT 스타일 말풍선 UI
- 봇 아바타
- 타이핑 점 애니메이션
- 자동 스크롤
- 중복 전송 방지
- 새로고침 없이 응답 표시
- 생각 모드
- 한국어 문장 후처리
- 오타/발음 보정
- 사용자가 알려준 오타 자동 학습
- Ollama 로컬 LLM 연결
- Ollama 실패 시 로컬 fallback
- Ctrl+V 이미지/동영상/파일 분석
- PPT/이미지/동영상/파일/EXE/사이트 추천/계산 의도 분류

## 가장 쉬운 실행

```powershell
scripts\START_PERFECT.bat
```

## Ollama 모델 설치

```powershell
scripts\INSTALL_OLLAMA_MODEL.bat
```

또는 직접:

```powershell
ollama pull llama3
```

## 직접 실행

```powershell
set PICK_LLM_MODE=auto
set PICK_OLLAMA_MODEL=llama3
python app.py
```

## 로컬 기본 모델만 실행

```powershell
scripts\START_LOCAL_ONLY.bat
```

## Ctrl+V 분석

1. 이미지/동영상/파일을 복사합니다.
2. PICK 화면에서 Ctrl+V를 누릅니다.
3. 파일 종류에 맞는 분석 화면으로 이동합니다.

## 오타 학습

예:

```text
헌타닉스 말고 헌트릭스야
```

또는:

```text
오타등록 헌타닉스=헌트릭스
```

다음부터 `헌타닉스`는 자동으로 `헌트릭스`로 보정됩니다.

## 생각 모드

예:

```text
생각해서 답해줘
왜 그런지 설명해줘
단계적으로 정리해줘
검토해서 말해줘
```

## 주의

이 버전은 구조와 기능을 통합한 최종판입니다.
다만 “완벽한 GPT급 지능”은 Ollama 모델 성능에 따라 달라집니다.
진짜 답변 품질을 크게 올리려면 llama3보다 더 강한 모델을 Ollama에 설치해서 사용하면 됩니다.
예: qwen2.5, llama3.1, mistral 등.


# PICK 자동화 시스템

추가된 파일:
- `automation.py`
- `scripts\START_AUTOMATION.bat`
- `scripts\AUTOMATION_ONCE.bat`
- `scripts\AUTOMATION_CHECK.bat`
- `scripts\AUTOMATION_REAL_TRAIN.bat`
- `scripts\AUTOMATION_VIRTUAL_TRAIN.bat`

## 가장 쉬운 실행

```powershell
scripts\START_AUTOMATION.bat
```

이 명령은 60분마다 자동으로 다음을 실행합니다.

- 상태 점검
- 대화 로그 백업
- 가상 학습 또는 자동 개선
- 자동화 리포트 저장

## 한 번만 실행

```powershell
scripts\AUTOMATION_ONCE.bat
```

## 상태 점검만 실행

```powershell
scripts\AUTOMATION_CHECK.bat
```

## 실제 학습 실행

```powershell
scripts\AUTOMATION_REAL_TRAIN.bat
```

주의:
실제 학습은 PC 성능과 데이터 양에 따라 오래 걸릴 수 있습니다.

## 생성 폴더

```text
backups/
automation_reports/
models/virtual_auto/
```

## 자동화 모드

```powershell
python automation.py --mode check --once
python automation.py --mode virtual --once
python automation.py --mode real --once
python automation.py --mode auto --minutes 60
```
