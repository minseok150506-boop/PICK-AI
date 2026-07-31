@echo off
cd /d "%~dp0"
echo Step 1: Quick Tunnel settings
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup_quick_tunnel.ps1"
if errorlevel 1 goto :error
echo.
echo Step 2: Windows automatic startup
powershell -NoProfile -ExecutionPolicy Bypass -File ".\install_windows_startup.ps1"
if errorlevel 1 goto :error
echo.
echo Setup completed.
echo Starting PICK Home AI Server now...
start "PICK Home AI Server" powershell -NoProfile -ExecutionPolicy Bypass -File ".\start_pick_home_server.ps1"
exit /b 0
:error
echo.
echo Setup failed. Check the error above.
pause
exit /b 1
