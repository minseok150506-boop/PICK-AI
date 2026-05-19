@echo off
chcp 65001 >nul
title PICK AI - Windows 시작 자동 실행 안내
echo.
echo ================================
echo Windows 시작 시 자동 실행 안내
echo ================================
echo.
echo 안정적인 자동 실행은 바로가기 방식이 가장 쉽습니다.
echo.
echo 1. Win + R 누르기
echo 2. shell:startup 입력
echo 3. 02_START_OLLAMA_SERVER.bat 바로가기 넣기
echo 4. 03_START_CLOUDFLARE_TUNNEL.bat 바로가기 넣기
echo.
echo 주의:
echo - PC가 켜져 있어야 PICK 사이트가 Ollama를 사용할 수 있습니다.
echo - Cloudflare Tunnel 주소가 매번 바뀔 수 있습니다.
echo - 주소가 바뀌면 Render Environment의 PICK_OLLAMA_HOST도 바꿔야 합니다.
echo.
pause
