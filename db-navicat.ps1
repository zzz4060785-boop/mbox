[CmdletBinding()]
param(
    [int]$LocalPort = 15432
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Server = "root@104.105.144.104"
$SshKey = Join-Path $env:USERPROFILE ".ssh\friendary_cafe24_ed25519"
$DatabaseHost = "127.0.0.1"
$DatabasePort = 5432

if (-not (Test-Path -LiteralPath $SshKey)) {
    throw "SSH key not found: $SshKey"
}

$PortInUse = Get-NetTCPConnection `
    -LocalPort $LocalPort `
    -State Listen `
    -ErrorAction SilentlyContinue

if ($PortInUse) {
    throw "Local port $LocalPort is already in use. Close the existing tunnel or run: .\db-navicat.ps1 -LocalPort 15433"
}

$PasswordScript = @'
set -eu
cd /opt/friendary
DATABASE_ASSIGNMENT="$(grep '^DATABASE_URL=' /etc/friendary/env | head -n 1)"
runuser -u appuser -- env "$DATABASE_ASSIGNMENT" \
    /opt/friendary/.venv/bin/python -c \
    'import os; from sqlalchemy.engine import make_url; print(make_url(os.environ["DATABASE_URL"]).password)'
'@
$PasswordScriptBase64 = [Convert]::ToBase64String(
    [Text.Encoding]::UTF8.GetBytes($PasswordScript)
)
$DatabasePassword = & ssh.exe `
    -i $SshKey `
    -o BatchMode=yes `
    $Server `
    "echo '$PasswordScriptBase64' | base64 -d | bash"

if ($LASTEXITCODE -ne 0 -or -not $DatabasePassword) {
    throw "Could not retrieve the database password from Cafe24."
}

Set-Clipboard -Value ($DatabasePassword.Trim())
$DatabasePassword = $null

Write-Host "Cafe24 PostgreSQL tunnel" -ForegroundColor Cyan
Write-Host ""
Write-Host "DBeaver/Navicat connection settings:" -ForegroundColor Yellow
Write-Host "  Connection type : PostgreSQL"
Write-Host "  Host            : 127.0.0.1"
Write-Host "  Port            : $LocalPort"
Write-Host "  Database        : appdb"
Write-Host "  User name       : appuser"
Write-Host "  Password        : Copied to the Windows clipboard"
Write-Host ""
Write-Host "Paste the password with Ctrl+V when DBeaver asks." -ForegroundColor Green
Write-Host "Keep this window open while using DBeaver or Navicat." -ForegroundColor Green
Write-Host "Press Ctrl+C to close the database tunnel." -ForegroundColor Green

& ssh.exe `
    -i $SshKey `
    -o BatchMode=yes `
    -o ExitOnForwardFailure=yes `
    -o ServerAliveInterval=30 `
    -o ServerAliveCountMax=3 `
    -N `
    -L "${LocalPort}:${DatabaseHost}:${DatabasePort}" `
    $Server

if ($LASTEXITCODE -ne 0) {
    throw "SSH database tunnel stopped with exit code $LASTEXITCODE."
}
