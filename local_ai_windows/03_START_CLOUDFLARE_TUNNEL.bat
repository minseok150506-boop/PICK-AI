@echo off
chcp 65001 >nul
title PICK AI - Cloudflare Tunnel 실행
echo.
echo ================================
echo PICK AI - Cloudflare Tunnel 실행
echo ================================
echo.

where cloudflared >nul 2>nul
if errorlevel 1 (
  echo [오류] cloudflared가 설치되어 있지 않습니다.
  echo Cloudflare 공식 다운로드 페이지에서 Windows용 cloudflared를 설치하세요.
  echo https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/
  pause
  exit /b 1
)

echo.
echo Ollama 로컬 서버를 외부 주소로 연결합니다.
echo 아래에 나오는 https://xxxxx.trycloudflare.com 주소를 복사하세요.
echo.
echo Render Environment에 이렇게 넣으세요:
echo PICK_AI_PROVIDER=ollama
echo PICK_OLLAMA_MODEL=gemma3:12b 또는 qwen3:8b
echo PICK_OLLAMA_HOST=https://xxxxx.trycloudflare.com
echo.
echo 이 창은 끄지 마세요. 끄면 PICK 사이트와 Ollama 연결이 끊깁니다.
echo.

cloudflared tunnel --url http://127.0.0.1:11434

pause
