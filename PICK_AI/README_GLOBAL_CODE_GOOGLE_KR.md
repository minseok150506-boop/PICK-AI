# PICK AI — 코딩 + 전 세계 언어 + Google 로그인

## 1. 코딩 기능

PICK은 코딩 질문을 자동 감지합니다.

자동 우선순위:
1. `qwen2.5-coder:14b`
2. `qwen2.5-coder:7b`
3. `qwen3:8b`
4. `qwen3:4b`

설치된 모델만 실제로 선택합니다.

30만 원대 MiniPC + RAM 32GB에서는 우선 다음 조합을 권장합니다.

```powershell
ollama pull qwen3:8b
ollama pull qwen3:4b
ollama pull qwen2.5-coder:7b
ollama pull llava
```

코딩 답변은:
- 파일명
- 코드 위치
- 실행 명령
- 오류 원인
- 수정 코드
- 코드 블록
을 명확하게 표시하도록 프롬프트가 강화되어 있습니다.

## 2. 전 세계 언어

기본은 자동 감지입니다.

지원 선택 항목:
- 한국어
- 영어
- 일본어
- 중국어 간체/번체
- 스페인어
- 프랑스어
- 독일어
- 이탈리아어
- 포르투갈어
- 러시아어
- 아랍어
- 힌디어
- 인도네시아어
- 베트남어
- 태국어
- 터키어
- 폴란드어
- 네덜란드어
- 스웨덴어
- 우크라이나어

Ollama 모델 자체가 해당 언어를 잘 지원할수록 답변 품질도 좋아집니다.

## 3. Google 로그인

기존 PICK 아이디/비밀번호 로그인은 그대로 유지됩니다.

Google 로그인을 쓰려면 Google OAuth 2.0 Web Client가 필요합니다.

Synology `.env`:

```text
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

Google OAuth의 Authorized redirect URI에는 실제 PICK HTTPS 주소의 다음 경로를 등록해야 합니다.

```text
https://PICK주소/auth/google/callback
```

예:

```text
https://pick.example.com/auth/google/callback
```

Client ID/Secret이 비어 있으면 Google 로그인 버튼은 자동으로 숨겨집니다.

## 4. 구조

외부 사용자
→ Synology HTTPS
→ PICK 웹 / 로그인 / DB / 인터넷 검색
→ 내부 LAN
→ MiniPC Ollama
→ 일반 AI / 코딩 AI / 이미지·영상 분석

Render는 사용하지 않습니다.
이미지·동영상 생성은 사용하지 않습니다.
