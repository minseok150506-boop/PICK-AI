$ErrorActionPreference = "Stop"


Set-Location $PSScriptRoot
Write-Host "=== PICK AI 실행 및 자동 복구 ===" -ForegroundColor Cyan
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher(py)를 찾지 못했습니다. Python 3.11 또는 3.12를 설치해 주세요."
}
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[1/5] 전용 Python 환경 생성" -ForegroundColor Yellow
    py -3 -m venv .venv
}
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
Write-Host "[2/5] pip 업데이트" -ForegroundColor Yellow
& $python -m pip install --upgrade pip
Write-Host "[3/5] 패키지 설치/업데이트" -ForegroundColor Yellow
& $python -m pip install -r requirements.txt
Write-Host "[4/5] 자가진단" -ForegroundColor Yellow
& $python PICK_DOCTOR.py
if ($LASTEXITCODE -ne 0) { throw "PICK 자가진단에 실패했습니다." }
Write-Host "[5/5] PICK AI 시작" -ForegroundColor Green
$env:PICK_SECRET_KEY = "pick-local-change-this-secret"
& $python app.py
