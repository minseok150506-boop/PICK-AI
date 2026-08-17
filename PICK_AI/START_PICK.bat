@echo off
chcp 949 >nul
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title PICK AI Recovery Launcher

echo ==============================================
echo            PICK AI 실행 및 자동 복구
echo ==============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo [오류] Python을 찾지 못했습니다.
  echo Python 3.11 또는 3.12를 설치한 뒤 다시 실행하세요.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] 전용 Python 환경을 만듭니다...
  py -3 -m venv .venv
  if errorlevel 1 goto :fail
)

echo [2/5] pip를 확인합니다...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [3/5] PICK 필수 패키지를 설치/업데이트합니다...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [4/5] 데이터베이스와 서버를 검사합니다...
".venv\Scripts\python.exe" PICK_DOCTOR.py
if errorlevel 1 goto :doctor_fail

echo [5/5] PICK AI를 시작합니다...
set PICK_SECRET_KEY=pick-local-change-this-secret
".venv\Scripts\python.exe" app.py
goto :end

:doctor_fail
echo.
echo [오류] PICK 자가진단에서 문제가 발견되었습니다.
echo 위에 표시된 FAIL 내용을 보내주시면 정확히 고칠 수 있습니다.
pause
exit /b 2

:fail
echo.
echo [오류] 설치 또는 실행 준비에 실패했습니다.
echo 인터넷 연결과 Python 설치 상태를 확인하세요.
pause
exit /b 1

:end
pause
