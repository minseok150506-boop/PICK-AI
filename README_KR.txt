PICK v5 Brain Ollama

추가 기능:
- 유추 모드
- PICK Brain 인공신경망형 의도 분류기
- 시간/유튜브/검색/개발/일반대화 자동 분류
- 모르는 단어 검색
- 오타 보정
- 회원가입/로그인/채팅 저장/채팅 삭제
- GPT API 없음, Ollama 전용

Cloudflare:
cloudflared tunnel --http-host-header localhost --url http://127.0.0.1:11434

Render Environment:
PICK_OLLAMA_HOST=https://xxxxx.trycloudflare.com
PICK_OLLAMA_MODEL=qwen3:8b
