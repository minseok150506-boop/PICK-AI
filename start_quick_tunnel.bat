@echo off
cd /d "%~dp0"
title PICK AI Quick Tunnel Manager
py -3 quick_tunnel_manager.py
if errorlevel 1 (
  echo.
  echo 실행 중 오류가 발생했습니다.
  pause
)
