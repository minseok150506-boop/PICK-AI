@echo off
chcp 949 >nul
title PICK STRONGEST MODEL INSTALL
echo qwen2.5:32b 모델을 설치합니다.
echo 시간이 오래 걸릴 수 있습니다.
ollama pull qwen2.5:32b
pause
