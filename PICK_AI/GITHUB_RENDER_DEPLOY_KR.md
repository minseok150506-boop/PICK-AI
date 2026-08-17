# PICK AI — GitHub + Render 배포

이 버전은 GitHub → Render 자동 배포용입니다.

## 1. GitHub
ZIP을 풀고 `PICK_AI` 폴더 안의 파일 전부를 GitHub 저장소 루트에 올립니다.
예: `https://github.com/minseok150506-boop/PICK-AI`

GitHub 루트에 `app.py`, `requirements.txt`, `render.yaml`, `templates/`, `static/`가 바로 보여야 합니다.

## 2. Render
Render Dashboard → New → Blueprint → GitHub PICK-AI 저장소 연결 → render.yaml 적용.

정식 render.yaml은 Singapore 리전, Gunicorn, /healthz, GitHub 자동 배포, /var/data 1GB Persistent Disk를 사용합니다.

## 3. 환경변수
필수: `PICK_ADMIN_PASSWORD`

AI 답변을 실제로 쓰려면 `PICK_AI_BACKEND_URL`에 Render에서 접근 가능한 Ollama 호환 HTTPS AI 서버 주소를 넣습니다.
AI 서버가 없으면 웹/로그인/채팅/메모리/검색은 실행되지만 LLM 답변은 AI 백엔드 연결 안내가 나옵니다.

Google 로그인은 `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`을 입력하고 OAuth Redirect URI를 `https://YOUR-PICK.onrender.com/auth/google/callback`으로 등록합니다.

## 4. 자동 배포
GitHub에 push → Render 자동 Build → 자동 Deploy. Quick Tunnel/Deploy Hook은 필요 없습니다.

## 5. 데이터 보존
정식 render.yaml은 `/var/data` Persistent Disk를 사용해 SQLite DB, 계정, 사용자별 채팅, 메모리, 업로드, 학습 피드백을 보존합니다. Render Persistent Disk는 유료 Web Service가 필요합니다.

무료 테스트는 `render-free-test.yaml`을 사용할 수 있지만 무료 Web Service의 로컬 파일은 영구 저장되지 않으므로 재배포/재시작 시 데이터가 사라질 수 있습니다.

## 6. 사용자별 분리
기존 account isolation을 유지합니다. 다른 사용자는 타인의 채팅, 메시지, 메모리, 첨부파일, 프로필 메모리, 학습 피드백을 볼 수 없습니다.

## 7. 확인
배포 후 `/healthz` 확인. 로그인 후 `/api/render/status`에서 저장 경로, AI 백엔드, Google 로그인 설정 상태를 확인할 수 있습니다.
