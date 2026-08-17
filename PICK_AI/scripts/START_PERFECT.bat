@echo off
chcp 949 >nul
title PICK PERFECT FINAL
echo =====================================
echo PICK PERFECT FINAL 실행
echo =====================================
echo.
echo Ollama가 설치되어 있고 llama3가 있으면 자동으로 사용합니다.
echo 없으면 로컬 기본 모델로 실행됩니다.
echo.
set PICK_LLM_MODE=auto
set PICK_OLLAMA_MODEL=llama3
python app.py
pause
