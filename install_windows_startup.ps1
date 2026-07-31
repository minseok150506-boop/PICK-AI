$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$taskName = "PICK Home AI Server"
$scriptPath = Join-Path $PSScriptRoot "start_pick_home_server.ps1"

if (-not (Test-Path $scriptPath)) {
    throw "start_pick_home_server.ps1 was not found."
}
if (-not (Test-Path (Join-Path $PSScriptRoot ".pick_tunnel.env"))) {
    throw ".pick_tunnel.env was not found. Run setup_quick_tunnel.ps1 first."
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Host "Installed Windows startup task: $taskName" -ForegroundColor Green
Write-Host "PICK will start Ollama and Quick Tunnel automatically after Windows login." -ForegroundColor Green
