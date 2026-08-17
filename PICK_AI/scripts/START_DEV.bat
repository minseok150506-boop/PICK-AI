@echo off
chcp 949 >nul
title PICK DEV
set PICK_SECRET_KEY=pick-local-secret-change-me
set PICK_LLM_MODE=local
python app.py
pause
