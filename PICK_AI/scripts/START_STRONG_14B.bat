@echo off
chcp 949 >nul
title PICK STRONG 14B MODE
echo PICK 강력 LLM 모드로 실행합니다.
set PICK_LLM_MODE=auto
set PICK_OLLAMA_MODEL=qwen2.5:14b
python app.py
pause
