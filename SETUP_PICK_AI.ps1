Write-Host "PICK AI Ollama 자동 설정 시작"

winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements
winget install Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements

Start-Process "ollama"
Start-Sleep -Seconds 10

ollama pull qwen3:8b

Start-Process powershell -ArgumentList "ollama serve"
Start-Sleep -Seconds 5

Start-Process powershell -ArgumentList "cloudflared tunnel --url http://localhost:11434"

Write-Host ""
Write-Host "Cloudflare 창에 나오는 https://xxxxx.trycloudflare.com 주소를 복사하세요."
Write-Host "그 주소를 Render Environment의 PICK_OLLAMA_HOST에 넣으세요."
pause
