@echo off
chcp 65001 >nul
title PICK AI - Ollama 모델 설치
echo.
echo ================================
echo PICK AI - Ollama 모델 설치
echo ================================
echo.

where ollama >nul 2>nul
if errorlevel 1 (
  echo [오류] Ollama가 설치되어 있지 않습니다.
  echo 먼저 https://ollama.com/download 에서 Windows용 Ollama를 설치하세요.
  pause
  exit /b 1
)

echo 사용할 모델을 선택하세요.
echo.
echo 1. gemma3:12b  ^(분석/추론 좋음, 조금 무거움^)
echo 2. qwen3:8b    ^(한국어/대화 자연스러움, 추천^)
echo.
set /p MODEL_CHOICE=번호 입력 ^(기본 1^): 

if "%MODEL_CHOICE%"=="2" (
  set PICK_MODEL=qwen3:8b
) else (
  set PICK_MODEL=gemma3:12b
)

echo.
echo 선택 모델: %PICK_MODEL%
echo 모델 다운로드/실행 준비 중...
ollama pull %PICK_MODEL%

echo.
echo 완료되었습니다.
echo 다음 단계: 02_START_OLLAMA_SERVER.bat 실행
pause
