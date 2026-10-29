[CmdletBinding()]
param(
    [int]$Port = 8765,
    [string]$Distro = "Ubuntu",
    [string]$WslUser = ""
)

$ErrorActionPreference = "Stop"
$ServerPath = Join-Path $PSScriptRoot "web\server.py"

$Arguments = @("`"$ServerPath`"", "--port", "$Port", "--distro", $Distro)
if ($WslUser) {
    $Arguments += @("--wsl-user", $WslUser)
}

Start-Process python.exe -ArgumentList $Arguments -WindowStyle Minimized
Start-Sleep -Seconds 2
Start-Process chrome.exe "http://127.0.0.1:$Port"
