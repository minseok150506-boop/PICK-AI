@echo off
chcp 949 >nul
title PICK SERVICE LOCAL
set PICK_SECRET_KEY=pick-local-secret
set PICK_LLM_MODE=auto
python app.py
pause
