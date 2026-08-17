@echo off
chcp 949 >nul
title PICK AI

echo ==========================================
echo          PICK AI 실행
echo ==========================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo 가상환경을 생성합니다...
  py -m venv .venv
)

echo 필수 패키지를 확인합니다...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo PICK AI를 시작합니다.
echo 브라우저에서 서버 주소로 접속해 주세요.
echo.

".venv\Scripts\python.exe" app.py

echo.
echo PICK AI가 종료되었습니다.
pause
