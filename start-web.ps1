[CmdletBinding()]
param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$ServerPath = Join-Path $PSScriptRoot "web\server.py"

Start-Process python.exe -ArgumentList "`"$ServerPath`"", "--port", "$Port" -WindowStyle Minimized
Start-Sleep -Seconds 2
Start-Process chrome.exe "http://127.0.0.1:$Port"
