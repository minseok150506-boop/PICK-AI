$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

function Test-Ollama {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

Write-Host "=== PICK Home AI Server ===" -ForegroundColor Cyan

if (-not (Test-Path ".pick_tunnel.env")) {
    Write-Host "Missing .pick_tunnel.env. Run setup_quick_tunnel.ps1 first." -ForegroundColor Red
    exit 2
}

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "cloudflared was not found. Install it or set CLOUDFLARED_PATH in .pick_tunnel.env." -ForegroundColor Red
    exit 3
}

if (-not (Test-Ollama)) {
    Write-Host "Starting Ollama..." -ForegroundColor Yellow
    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollama) {
        Write-Host "Ollama was not found. Install Ollama first." -ForegroundColor Red
        exit 4
    }
    Start-Process -FilePath $ollama.Source -ArgumentList "serve" -WindowStyle Hidden

    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 2
        if (Test-Ollama) { $ready = $true; break }
    }
    if (-not $ready) {
        Write-Host "Ollama did not start within 60 seconds." -ForegroundColor Red
        exit 5
    }
}

Write-Host "Ollama is ready. Starting Quick Tunnel manager..." -ForegroundColor Green
py -3 ".\quick_tunnel_manager.py"
