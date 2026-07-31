# 빠른 시작

## Windows 로컬 실행

```powershell
scripts\INSTALL_REQUIREMENTS.bat
scripts\START_WINDOWS_SERVICE.bat
```

접속:

```text
http://127.0.0.1:5000
```

## Render 배포

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

환경변수:

```text
PICK_SECRET_KEY=긴랜덤문자
PICK_LLM_MODE=local
```

Render 배포 후 HTTPS 주소가 자동 생성됩니다.
