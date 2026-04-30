# PICK 처음부터 다시 만든 클린 버전

## Render 배포

GitHub 저장소 루트에 아래 파일이 바로 보여야 합니다.

- app.py
- requirements.txt
- templates/
- static/
- Procfile
- render.yaml

Render 설정:

Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app

환경변수:
PICK_SECRET_KEY=긴랜덤문자열

## 로컬 실행

```powershell
scripts\START_LOCAL.bat
```

접속:
http://127.0.0.1:5000

## 기능

- 회원가입 / 로그인
- 한글 아이디, 비밀번호 차단
- 첫 번째 가입자 자동 관리자
- 관리자 유저 관리
- 새 채팅
- 메시지 DB 저장
- ChatGPT식 UI
- PICK 브랜드 적용
