@echo off
title PICK WINDOWS SERVICE
echo PICK Windows 서비스 서버를 실행합니다.
echo 접속: http://127.0.0.1:5000
set PICK_SECRET_KEY=pick-local-secret-change-me
set PICK_LLM_MODE=local
python -m waitress --listen=0.0.0.0:5000 app:app
pause
