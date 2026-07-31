# PICK 사이드바 제거 + UI 수정 버전

변경점:
- 왼쪽 기능 버튼 제거
- 사이드바에는 새 채팅 / 최근 채팅 / 로그아웃만 남김
- 기능은 점 3개 메뉴 또는 대화로 실행
- 메시지 우측 상단 붙는 문제 수정
- 말풍선 줄바꿈 문제 수정

실행:
pip install -r requirements.txt
python app.py

- Enter 연타/버튼 연타 중복 전송 방지 추가


추가 기능:
- 사이트 추천 기능 추가
- 예:
  - 이미지 사이트 추천해줘
  - ppt 템플릿 사이트 추천해줘
  - 코딩 사이트 알려줘
  - 게임 에셋 사이트 추천해줘
- 추천 결과의 URL은 클릭 가능


추가 수정:
- 우측 아래 BUILD 문구 제거
- 사이드바의 'AI 통합 버전' 문구 제거
- 기본 AI 모델을 더 빠른 기본값으로 변경
- 전송 중 '전송중' 표시 추가
- Flask debug 모드 비활성화로 체감 속도 개선


하이브리드 GPT급 버전:
- 메뉴 이동 / PPT / 이미지 / 동영상 / 파일 / EXE / 사이트 추천은 로컬 처리
- 설명, 요약, 비교, 긴 질문 같은 자연 대화만 AI 호출
- OPENAI_API_KEY가 없거나 응답 실패 시 로컬 응답으로 자동 전환
- 기본값은 빠른 모델 우선


추가 수정:
- 일반 대화는 거의 전부 AI 사용
- 도구 실행형 명령만 로컬 우선 처리
- 기본 AI 모델을 gpt-5-mini로 변경
- fallback 문구를 덜 어색하게 수정


추가 수정:
- 연산 처리 기능 추가
- 예:
  - 계산해줘 12*(3+4)
  - 100/4+7
  - (15-3)*8
- 사칙연산, 나머지, 괄호 지원


엔진 고도화:
- 의도 분류기(classify_intent_v2)
- 상태 요약(summarize_state)
- 되묻기 엔진(need_clarification)
- 계획 생성(make_plan_v2)
- 도구 선택(choose_tool)
- 실행기(execute_plan_v2)
- 답변 검수(review_reply_v2)
- 실패 복구 포함


실시간 채팅 수정:
- 새로고침 없이 응답 즉시 표시
- Enter 연타/중복 전송 방지 강화
- 전송 중 버튼/입력창 잠금
- 오류 발생 시 채팅창에 바로 표시


최종 전송 흐름 보강:
- Enter 연타 중복 전송 방지
- 전송 버튼 연타 방지
- 전송 중 입력창/버튼 잠금
- 새로고침 없이 응답 즉시 렌더링
- 오류 발생 시 채팅창에 바로 표시


PICK Engine 추가:
- pick_engine.py 파일 추가
- 대화 분류, 상태 기억, 계획 생성, 도구 라우팅, 답변 검수 담당
- app.py는 엔진을 호출하는 구조로 변경
- 외부 API 없이 로컬 엔진으로 동작


PICK LLM 모델 계층 추가:
- pick_llm.py 추가
- 외부 API 없이 동작하는 PickLocalLLM 포함
- Ollama 호환 로컬 LLM 서버 연결 가능
- PICK_LLM_MODE 설정:
  - local: 내장 로컬 사고 모델
  - ollama: Ollama 서버 사용
  - auto: Ollama 실패 시 local fallback

사용 예:
기본 로컬 모델:
python app.py

Ollama 사용:
set PICK_LLM_MODE=ollama
set PICK_OLLAMA_MODEL=llama3
python app.py

Ollama 서버는 별도로 실행되어 있어야 합니다:
ollama run llama3


# Ollama 연결 + ChatGPT 스타일 UI

## 1. Ollama 설치
https://ollama.com 에서 설치합니다.

## 2. 모델 받기
```powershell
ollama pull llama3
```

또는:
```powershell
scripts\pull_llama3.bat
```

## 3. PICK 실행
```powershell
set PICK_LLM_MODE=auto
set PICK_OLLAMA_MODEL=llama3
python app.py
```

또는:
```powershell
scripts\run_with_ollama.bat
```

## 모드
- PICK_LLM_MODE=auto : Ollama 우선, 실패하면 로컬 fallback
- PICK_LLM_MODE=ollama : Ollama만 사용
- PICK_LLM_MODE=local : 내장 로컬 모델만 사용

## ChatGPT 스타일 UI 개선
- 메시지 중앙 정렬
- 말풍선 여백/줄바꿈 개선
- 입력창 ChatGPT 스타일 보강
- 점 3개 메뉴 스타일 개선


# PICK Rebuild Ollama + ChatGPT UI

## Ollama 모델 설치
```powershell
ollama pull llama3
```

또는:
```powershell
scripts\pull_llama3.bat
```

## Ollama 연결 실행
```powershell
scripts\run_with_ollama.bat
```

직접 실행:
```powershell
set PICK_LLM_MODE=auto
set PICK_OLLAMA_MODEL=llama3
python app.py
```

## 로컬 기본 모델만 실행
```powershell
scripts\run_local_only.bat
```

모드:
- auto: Ollama 우선, 실패하면 로컬 fallback
- ollama: Ollama만 사용
- local: 로컬 기본 모델만 사용


# 자동 오타 학습 + 한국어 발음 보정 + GPT식 이해 강화

추가된 파일:
- `pick_typo.py`
- `data/corrections.json` 자동 생성
- `scripts/show_corrections.bat`

## 자동 학습 예시

사용자:
```text
헌타닉스 말고 헌트릭스야
```

PICK:
```text
헌타닉스 → 헌트릭스로 기억했습니다.
```

다음부터:
```text
헌타닉스 설명해줘
```

자동으로:
```text
헌트릭스 설명해줘
```

로 보정됩니다.

## 기본 보정 내장
- 헌타닉스 → 헌트릭스
- 헌트닉스 → 헌트릭스
- 피피티 → PPT
- 이미지열어줘 → 이미지 분석 열어줘
- 동영상열어줘 → 동영상 분석 열어줘
- 파일열어줘 → 파일 분석 열어줘

## 실행
```powershell
scripts\run_with_ollama_korean.bat
```


# 스마트 이해 최종 보강

이번 버전은 오타를 무조건 바꾸는 방식이 아니라, 더 안전한 방식으로 보정합니다.

## 핵심 개선
- 자동 오타 학습
- 발음 유사어 보정
- 고유명사 보호
- 과한 자동 보정 방지
- 보정 내역 저장
- 사용자가 직접 가르친 단어 기억

## 사용 예시

```text
헌타닉스 말고 헌트릭스야
```

또는:

```text
오타등록 헌타닉스=헌트릭스
```

이후:

```text
헌타닉스 설명해줘
```

자동으로 `헌트릭스 설명해줘`로 보정됩니다.

## 보정 목록 확인

```powershell
scripts\show_corrections.bat
```

## 보정 목록 초기화

```powershell
scripts\clear_corrections.bat
```

## 실행

```powershell
scripts\run_with_ollama_korean.bat
```


# ChatGPT 최종 UI + 문장 교정 + 생각 모드 + 기억 강화

추가:
- `pick_polish.py`
- 한국어 문장 후처리
- 어색한 문구 보정
- 생각 모드 표시
- 타이핑 점 애니메이션
- ChatGPT식 말풍선 구조
- 봇 아바타 추가
- 스크롤 자동 보정
- 대화 상태 기반 답변 후처리

생각 모드 사용:
```text
생각해서 답해줘
왜 그런지 설명해줘
단계적으로 정리해줘
검토해서 말해줘
```

실행:
```powershell
scripts\run_with_ollama_korean.bat
```


# Ctrl+V 파일/동영상/이미지 분석

이번 버전은 Ctrl+V 붙여넣기로 업로드를 처리합니다.

## 사용 방법
1. 이미지/동영상/파일을 복사합니다.
2. PICK 화면에서 Ctrl+V를 누릅니다.
3. 파일 종류를 자동 판단합니다.
4. 이미지면 이미지 분석 화면, 동영상이면 동영상 분석 화면, 일반 파일이면 파일 분석 화면으로 이동합니다.

## 지원
- 이미지: png, jpg, jpeg, gif, webp, bmp
- 동영상: mp4, mov, avi, mkv, webm
- 파일: txt, md, csv, json, pdf, docx, pptx, xlsx, py, js, html, css 등

주의:
브라우저/운영체제에 따라 Ctrl+V로 동영상이나 일반 파일 붙여넣기는 제한될 수 있습니다.
이미지 캡처 붙여넣기는 대부분 잘 동작합니다.
