@echo off
chcp 949 >nul
echo [PICK] Ollama 연결 모드로 실행합니다.
set PICK_LLM_MODE=auto
set PICK_OLLAMA_MODEL=llama3
python app.py
pause
