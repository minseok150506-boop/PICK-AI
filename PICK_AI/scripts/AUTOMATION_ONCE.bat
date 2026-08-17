@echo off
chcp 949 >nul
title PICK AUTOMATION ONCE
echo PICK 자동화를 한 번 실행합니다.
python automation.py --mode auto --once
pause
