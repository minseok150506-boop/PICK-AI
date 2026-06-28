PICK V9 Final Ollama

기능:
- 답변 전 인터넷 검색 강화
- 검색 결과를 Ollama 프롬프트에 넣고 답변
- 전 세계 도시 날씨 지원
- 유튜브 검색 링크
- Google/네이버 검색 노출용 SEO 구조
- robots.txt 자동 제공
- sitemap.xml 자동 제공
- /about 소개 페이지
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

Google:
Google Search Console 등록 후 /sitemap.xml 제출

Naver:
네이버 서치어드바이저 등록 후 /sitemap.xml 제출
