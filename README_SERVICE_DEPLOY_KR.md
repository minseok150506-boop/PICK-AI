
# PICK 서비스 배포판

추가된 기능:
- 회원가입
- 로그인
- 로그아웃
- SQLite DB
- 사용자별 대화 저장 구조
- 관리자 상태 페이지
- Render 배포 설정
- Dockerfile
- gunicorn 실행 설정

## 로컬 실행

```powershell
scripts\START_SERVICE_LOCAL.bat
```

브라우저:

```text
http://127.0.0.1:5000
```

처음 접속하면 로그인 화면이 나옵니다. 회원가입 후 사용하세요.

## 관리자 상태

```text
http://127.0.0.1:5000/admin/status
```

## DB 위치

```text
data/pick_service.db
```

## Render 배포

1. GitHub에 이 폴더 업로드
2. Render에서 New Web Service 생성
3. Build Command:

```bash
pip install -r requirements.txt
```

4. Start Command:

```bash
gunicorn app:app
```

5. 환경변수:

```text
PICK_SECRET_KEY=아무 긴 랜덤 문자열
PICK_LLM_MODE=local
```

주의:
Render 무료 서버에서는 로컬 Ollama를 직접 돌리기 어렵습니다.
Ollama까지 쓰려면 VPS나 GPU 서버가 필요합니다.

## Docker 실행

```bash
docker build -t pick-ai-service .
docker run -p 5000:5000 -e PICK_SECRET_KEY=change-me pick-ai-service
```

## VPS 배포

```bash
pip install -r requirements.txt
gunicorn app:app -b 0.0.0.0:5000
```

Nginx를 붙이면 도메인 연결이 가능합니다.
