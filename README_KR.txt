PICK V13 Polished Auto

수정 사항:
- 로그인 화면 더 깔끔하게 정리
- '김민석님이 만든 Search + Weather AI' 제거 유지
- 'PICK 소개' 링크 제거 유지
- Brain 표시 제거 유지
- Thinking 표시 제거 유지
- 내부 추론은 사용자에게 표시하지 않음
- ChatGPT처럼 깔끔한 UI
- 인터넷 자동 검색
- Wikipedia 보조 검색 추가
- GitHub 검색 링크 보조 추가
- Ollama 자동 연결
- Ollama 실패 시 인터넷 검색 fallback
- 로그인/회원가입 유지
- 채팅 저장/삭제 유지
- 전 세계 날씨
- 유튜브 검색 링크
- 뉴스/검색 자동 처리
- 제작자 김민석 고정
- GPT API 없음, Ollama 전용

GitHub에는 기존 파일을 전부 삭제하고 이 ZIP 안 파일만 업로드하세요.

Render Environment:
PICK_OLLAMA_HOST=https://xxxxx.trycloudflare.com
PICK_OLLAMA_MODEL=qwen3:8b
PUBLIC_SITE_URL=https://pick-ai.onrender.com

Cloudflare:
cloudflared tunnel --http-host-header localhost --url http://127.0.0.1:11434

중요:
Cloudflare quick tunnel 주소가 바뀌면 Render 환경변수 PICK_OLLAMA_HOST도 반드시 새 주소로 바꿔야 합니다.
