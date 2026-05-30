Write-Host "PICK AI 설치 시작"

winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements
winget install Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements

Start-Process "ollama"

Start-Sleep -Seconds 10

ollama pull qwen3:8b

Start-Process powershell -ArgumentList "ollama serve"

Start-Sleep -Seconds 5

Start-Process powershell -ArgumentList "cloudflared tunnel --url http://localhost:11434"

pause
