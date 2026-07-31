@echo off
title PICK AUTOMATION CHECK
echo PICK 상태 점검과 백업만 실행합니다.
python automation.py --mode check --once
pause
