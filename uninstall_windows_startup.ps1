$ErrorActionPreference = "SilentlyContinue"
Unregister-ScheduledTask -TaskName "PICK Home AI Server" -Confirm:$false
Write-Host "Removed Windows startup task: PICK Home AI Server" -ForegroundColor Green
