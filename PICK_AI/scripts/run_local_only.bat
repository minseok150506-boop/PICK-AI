@echo off
chcp 949 >nul
echo [PICK] 로컬 기본 모델만 사용합니다.
set PICK_LLM_MODE=local
python app.py
pause
