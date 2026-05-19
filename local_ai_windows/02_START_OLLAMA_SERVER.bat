@echo off
chcp 65001 >nul
title PICK AI - Ollama 서버 실행
echo.
echo ================================
echo PICK AI - Ollama 서버 실행
echo ================================
echo.

where ollama >nul 2>nul
if errorlevel 1 (
  echo [오류] Ollama가 설치되어 있지 않습니다.
  pause
  exit /b 1
)

echo 모델을 선택하세요.
echo.
echo 1. gemma3:12b
echo 2. qwen3:8b
echo.
set /p MODEL_CHOICE=번호 입력 ^(기본 1^): 

if "%MODEL_CHOICE%"=="2" (
  set PICK_MODEL=qwen3:8b
) else (
  set PICK_MODEL=gemma3:12b
)

REM Ollama 서버 주소. Cloudflare Tunnel은 이 로컬 주소를 외부로 연결합니다.
set OLLAMA_HOST=127.0.0.1:11434

REM 모델을 오래 메모리에 유지해서 다음 답변 속도를 높입니다.
set OLLAMA_KEEP_ALIVE=30m

echo.
echo Ollama 서버를 실행합니다.
echo 모델: %PICK_MODEL%
echo 주소: http://127.0.0.1:11434
echo.
echo 이 창은 끄지 마세요.
echo.

start "PICK Ollama Model Warmup" cmd /c "ollama run %PICK_MODEL%"

ollama serve
pause
