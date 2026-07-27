PICK V10 Auto Web Ollama

핵심 수정:
- Ollama 연결 실패 시에도 대화가 멈추지 않음
- 인터넷 검색 결과 기반 fallback 답변 제공
- 인터넷 + Ollama 자동 사용
- 전 세계 날씨 지원
- 유튜브 검색 링크
- 상태 버튼에서 인터넷/Ollama 상태 확인
- 제작자 김민석 고정
- 네이버/OpenAI/Google 제작 오답 방지
- 회원가입/로그인/채팅 저장/삭제
- GPT API 없음, Ollama 전용

GitHub에는 기존 파일을 전부 삭제하고 이 ZIP 안 파일만 업로드하세요.

Render Environment:
PICK_OLLAMA_HOST=https://xxxxx.trycloudflare.com
PICK_OLLAMA_MODEL=qwen3:8b
PUBLIC_SITE_URL=https://pick-ai.onrender.com

Cloudflare:
cloudflared tunnel --http-host-header localhost --url http://127.0.0.1:11434
