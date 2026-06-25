PICK v3 Full Ollama

기능:
- GPT API 없음
- Ollama 전용
- 회원가입/로그인/로그아웃
- 사용자별 채팅 저장
- 채팅 목록/새 채팅/삭제
- 현재 시간 답변
- 유튜브 검색 링크
- DuckDuckGo 인터넷 검색 참고
- 욕설/유해/성인/자해/개인정보/API 키 필터
- 모바일 최적화

업로드:
GitHub 기존 파일을 전부 삭제하고 이 ZIP 안의 파일만 올리세요.

Render Environment:
PICK_OLLAMA_HOST=https://xxxxx.trycloudflare.com
PICK_OLLAMA_MODEL=qwen3:8b

Cloudflare 실행:
cloudflared tunnel --http-host-header localhost --url http://127.0.0.1:11434
