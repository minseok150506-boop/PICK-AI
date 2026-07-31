$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== PICK Quick Tunnel 자동 설정 ===" -ForegroundColor Cyan
Write-Host "입력값은 이 PC의 .pick_tunnel.env 파일에만 저장됩니다. GitHub에 올리지 마세요." -ForegroundColor Yellow

$apiKey = Read-Host "Render API Key"
$serviceId = Read-Host "Render Service ID (srv-로 시작)"
$deployHook = Read-Host "Render Deploy Hook URL"

Add-Type -AssemblyName System.Web
$bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
$token = [Convert]::ToBase64String($bytes).Replace('+','-').Replace('/','_').TrimEnd('=')

$content = @"
# 자동 생성됨 - 절대 GitHub에 올리지 마세요.
RENDER_API_KEY=$apiKey
RENDER_SERVICE_ID=$serviceId
RENDER_DEPLOY_HOOK=$deployHook
PICK_OLLAMA_TOKEN=$token
OLLAMA_LOCAL_URL=http://127.0.0.1:11434
GATEWAY_HOST=127.0.0.1
GATEWAY_PORT=11435
CLOUDFLARED_PATH=cloudflared
"@

Set-Content -Path ".pick_tunnel.env" -Value $content -Encoding UTF8
Write-Host "설정 저장 완료: .pick_tunnel.env" -ForegroundColor Green
Write-Host "이제 start_quick_tunnel.bat 을 실행하세요." -ForegroundColor Green
