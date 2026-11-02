[CmdletBinding()]
param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$ServerPath = Join-Path $PSScriptRoot "web\server.py"

& python.exe $ServerPath --port $Port
