@echo off
cd /d "%~dp0"
py -3 quick_tunnel_manager.py
if errorlevel 1 (
  echo.
  echo PICK Quick Tunnel failed. Check the error above.
  pause
)
