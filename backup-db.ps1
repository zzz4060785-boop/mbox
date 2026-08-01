[CmdletBinding()]
param(
    [switch]$Download
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Server = "root@104.105.144.104"
$SshKey = Join-Path $env:USERPROFILE ".ssh\friendary_cafe24_ed25519"
$ProjectRoot = $PSScriptRoot
$LocalBackupDir = Join-Path $ProjectRoot "db-backups"

if (-not (Test-Path -LiteralPath $SshKey)) {
    throw "SSH key not found: $SshKey"
}

$RemoteScript = @'
set -eu
APP_PATH="/opt/friendary"
DATABASE_ASSIGNMENT="$(grep '^DATABASE_URL=' /etc/friendary/env | head -n 1)"
if [ -z "$DATABASE_ASSIGNMENT" ]; then
    echo "DATABASE_URL is missing from /etc/friendary/env" >&2
    exit 1
fi
mkdir -p "$APP_PATH/db-backups"
chown appuser:appuser "$APP_PATH/db-backups"
cd "$APP_PATH"
runuser -u appuser -- env "$DATABASE_ASSIGNMENT" \
    "$APP_PATH/.venv/bin/python" scripts/backup_postgres.py
'@
$RemoteScriptBase64 = [Convert]::ToBase64String(
    [Text.Encoding]::UTF8.GetBytes($RemoteScript)
)

Write-Host "Creating Cafe24 PostgreSQL backup..." -ForegroundColor Cyan
$RemoteBackupPath = & ssh.exe `
    -i $SshKey `
    -o BatchMode=yes `
    $Server `
    "echo '$RemoteScriptBase64' | base64 -d | bash"

if ($LASTEXITCODE -ne 0 -or -not $RemoteBackupPath) {
    throw "Database backup failed."
}
$RemoteBackupPath = $RemoteBackupPath.Trim()
Write-Host "Server backup created: $RemoteBackupPath" -ForegroundColor Green

if ($Download) {
    New-Item -ItemType Directory -Force -Path $LocalBackupDir | Out-Null
    & scp.exe `
        -i $SshKey `
        -o BatchMode=yes `
        "${Server}:$RemoteBackupPath" `
        $LocalBackupDir
    if ($LASTEXITCODE -ne 0) {
        throw "Database backup download failed."
    }
    Write-Host "Downloaded to: $LocalBackupDir" -ForegroundColor Green
}
