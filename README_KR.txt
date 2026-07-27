PICK V14 Final Simple Deploy

이 버전은 GitHub와 Render에 그대로 올리기 쉽게 정리한 최종형입니다.

포함 기능:
- ChatGPT처럼 깔끔한 UI
- Brain 표시 없음
- Thinking 표시 없음
- 내부 추론은 사용자에게 표시하지 않음
- 인터넷 자동 검색
- Wikipedia 보조 검색
- GitHub 검색 링크 보조
- 전 세계 날씨
- 유튜브 검색 링크
- Ollama 자동 연결
- Ollama 연결 실패 시에도 대화가 완전히 멈추지 않음
- 로그인/회원가입
- 채팅 저장/삭제
- Render 배포 가능
- 제작자 김민석 고정
- GPT API 없음

────────────────────────
1. GitHub에 올리는 방법
────────────────────────

1) 이 ZIP 파일 압축을 풉니다.
2) GitHub PICK-AI 저장소에 들어갑니다.
3) 기존 파일을 전부 삭제합니다.
4) 압축 푼 파일을 전부 업로드합니다.

반드시 이 파일들이 보여야 합니다.

app.py
requirements.txt
runtime.txt
render.yaml
templates
static
README_KR.txt

────────────────────────
2. Render 환경변수
────────────────────────

Render 서비스 > Environment 에 아래 3개를 넣으세요.

PICK_OLLAMA_HOST=https://새-cloudflare주소.trycloudflare.com
PICK_OLLAMA_MODEL=qwen3:8b
PUBLIC_SITE_URL=https://pick-ai.onrender.com

주의:
Cloudflare 주소가 바뀌면 PICK_OLLAMA_HOST도 반드시 새 주소로 바꿔야 합니다.

────────────────────────
3. PC에서 Ollama 실행
────────────────────────

CMD 또는 PowerShell:

ollama run qwen3:8b

다른 CMD 또는 PowerShell 창:

cloudflared tunnel --http-host-header localhost --url http://127.0.0.1:11434

나오는 주소 예시:

https://abcd-xxxx.trycloudflare.com

이 주소를 Render의 PICK_OLLAMA_HOST에 넣으세요.

────────────────────────
4. Render 재배포
────────────────────────

Render에서 Manual Deploy > Deploy latest commit 을 누릅니다.

────────────────────────
5. 로그인 기본 계정
────────────────────────

아이디:
minseok

비밀번호:
kms0506a!

회원가입도 가능합니다.

────────────────────────
6. 문제가 생기면
────────────────────────

상태 버튼을 누르세요.

인터넷: 정상
Ollama: 정상

이렇게 나오면 정상입니다.

Ollama가 연결 안 됨으로 나오면:
1) cloudflared 창이 켜져 있는지 확인
2) trycloudflare 주소가 바뀌었는지 확인
3) Render 환경변수 PICK_OLLAMA_HOST를 새 주소로 수정
4) Render 재배포
