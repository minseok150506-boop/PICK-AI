@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\start_pick_home_server.ps1"
if errorlevel 1 pause
