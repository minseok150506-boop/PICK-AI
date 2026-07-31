@echo off
title PICK STRONGEST LLM MODE
echo PICK 최강 LLM 모드로 실행합니다.
echo 기본 모델: qwen2.5:32b
echo 무거우면 qwen2.5:14b 또는 llama3로 내려가세요.
set PICK_LLM_MODE=auto
set PICK_OLLAMA_MODEL=qwen2.5:32b
python app.py
pause
