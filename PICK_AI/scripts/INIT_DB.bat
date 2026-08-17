@echo off
chcp 949 >nul
python -c "from app import init_service_db; init_service_db(); print('DB 초기화 완료')"
pause
