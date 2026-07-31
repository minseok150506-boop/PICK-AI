# PICK AI v3 Ultimate

## 핵심 기능

- ChatGPT 스타일 다크 UI
- Brain/Thinking 문구 비표시
- 로그인/회원가입
- 여러 채팅방, 저장, 삭제
- Ollama 자동 연결 및 로컬 fallback
- 인터넷 검색/날씨/뉴스/유튜브 도구 연결 구조
- 파일·이미지·동영상 붙여넣기 분석
- 자동 제목 및 대화 기억
- Windows/Render/Cloudflare 배포 파일 포함

## Windows에서 가장 쉬운 실행

1. Ollama 설치 후 모델 준비

```powershell
ollama pull qwen3:8b
```

2. 프로젝트 폴더에서 실행

```powershell
scripts\START_PERFECT.bat
```

3. 브라우저에서 접속

```text
http://127.0.0.1:5000
```

## Render에서 집 Ollama 연결

```powershell
cloudflared tunnel --http-host-header localhost --url http://127.0.0.1:11434
```

Render 환경변수 예시:

```text
PICK_OLLAMA_HOST=https://새주소.trycloudflare.com
PICK_OLLAMA_MODEL=qwen3:8b
```

Quick Tunnel 주소는 다시 실행할 때 바뀔 수 있으므로 Render 환경변수도 갱신해야 합니다.

## 주의

실제 답변 성능은 설치된 Ollama 모델과 컴퓨터 성능에 따라 달라집니다. 인터넷 검색 공급자가 차단되거나 API 설정이 없으면 해당 기능은 제한될 수 있습니다.
