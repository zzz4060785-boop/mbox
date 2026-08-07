[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Server = "root@104.105.144.104"
$AppPath = "/opt/friendary"
$ServiceName = "friendary"
$SiteUrl = "https://zzz8247.mycafe24.com/"
$SshKey = Join-Path $env:USERPROFILE ".ssh\friendary_cafe24_ed25519"
$RemoteArchive = "/tmp/friendary-deploy.tar.gz"
$LocalArchive = Join-Path $env:TEMP "friendary-deploy.tar.gz"
$ProjectRoot = $PSScriptRoot

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath $SshKey)) {
    throw "SSH key not found: $SshKey"
}

$RequiredPaths = @(
    "pybo",
    "migrations",
    "deploy",
    "scripts",
    "config.py",
    "wsgi.py",
    "requirements.txt"
)

foreach ($RequiredPath in $RequiredPaths) {
    $FullPath = Join-Path $ProjectRoot $RequiredPath
    if (-not (Test-Path -LiteralPath $FullPath)) {
        throw "Required deployment path not found: $FullPath"
    }
}

Push-Location $ProjectRoot
try {
    Write-Host "[1/5] Creating deployment package..." -ForegroundColor Cyan
    if (Test-Path -LiteralPath $LocalArchive) {
        Remove-Item -LiteralPath $LocalArchive -Force
    }

    Invoke-CheckedCommand "tar.exe" @(
        "-czf", $LocalArchive,
        "--exclude=__pycache__",
        "--exclude=*.pyc",
        "pybo",
        "migrations",
        "deploy",
        "scripts",
        "config.py",
        "wsgi.py",
        "requirements.txt"
    )

    Write-Host "[2/5] Uploading package with SCP..." -ForegroundColor Cyan
    Invoke-CheckedCommand "scp.exe" @(
        "-i", $SshKey,
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        $LocalArchive,
        "${Server}:$RemoteArchive"
    )

    Write-Host "[3/5] Backing up and installing on Cafe24..." -ForegroundColor Cyan
    $RemoteDeploy = @'
set -eu
APP_PATH="/opt/friendary"
ARCHIVE="/tmp/friendary-deploy.tar.gz"
BACKUP_DIR="$APP_PATH/deploy-backups"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"
BACKUP_ITEMS=""
for item in pybo migrations deploy scripts config.py wsgi.py requirements.txt; do
    if [ -e "$APP_PATH/$item" ]; then
        BACKUP_ITEMS="$BACKUP_ITEMS $item"
    fi
done
if [ -n "$BACKUP_ITEMS" ]; then
    # Word splitting is intentional: the values come only from the fixed list above.
    tar -czf "$BACKUP_DIR/friendary-$STAMP.tar.gz" \
        -C "$APP_PATH" $BACKUP_ITEMS
fi

tar -xzf "$ARCHIVE" -C "$APP_PATH" --no-same-owner
chown -R appuser:www-data "$APP_PATH/pybo"
chown -R appuser:appuser "$APP_PATH/migrations" "$APP_PATH/deploy" "$APP_PATH/scripts"
chown appuser:appuser "$APP_PATH/config.py" "$APP_PATH/wsgi.py" "$APP_PATH/requirements.txt"

install -o root -g root -m 644 \
    "$APP_PATH/deploy/cafe24/friendary-db-backup.service" \
    /etc/systemd/system/friendary-db-backup.service
install -o root -g root -m 644 \
    "$APP_PATH/deploy/cafe24/friendary-db-backup.timer" \
    /etc/systemd/system/friendary-db-backup.timer
systemctl daemon-reload
systemctl enable --now friendary-db-backup.timer

cd "$APP_PATH"
DATABASE_ASSIGNMENT="$(grep '^DATABASE_URL=' /etc/friendary/env | head -n 1)"
if [ -z "$DATABASE_ASSIGNMENT" ]; then
    echo "DATABASE_URL is missing from /etc/friendary/env" >&2
    exit 1
fi

mkdir -p "$APP_PATH/db-backups"
chown appuser:appuser "$APP_PATH/db-backups"
runuser -u appuser -- env "$DATABASE_ASSIGNMENT" \
    "$APP_PATH/.venv/bin/python" scripts/backup_postgres.py

runuser -u appuser -- env "$DATABASE_ASSIGNMENT" \
    "$APP_PATH/.venv/bin/flask" --app wsgi:app db upgrade

systemctl restart friendary
systemctl is-active --quiet friendary
rm -f "$ARCHIVE"
echo "Cafe24 service is active. Backup: $BACKUP_DIR/friendary-$STAMP.tar.gz"
'@

    $RemoteDeployLf = $RemoteDeploy.Replace("`r`n", "`n").Replace("`r", "`n")
    $RemoteDeployBase64 = [Convert]::ToBase64String(
        [Text.Encoding]::UTF8.GetBytes($RemoteDeployLf)
    )
    $RemoteCommand = "echo '$RemoteDeployBase64' | base64 -d | bash"

    Invoke-CheckedCommand "ssh.exe" @(
        "-i", $SshKey,
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        $Server,
        $RemoteCommand
    )

    Write-Host "[4/5] Checking the public site..." -ForegroundColor Cyan
    $Response = Invoke-WebRequest -Uri $SiteUrl -Method Head -TimeoutSec 20
    if ($Response.StatusCode -ne 200) {
        throw "Site returned HTTP $($Response.StatusCode)."
    }

    Write-Host "[5/5] Deployment completed: HTTP 200" -ForegroundColor Green
    Write-Host $SiteUrl -ForegroundColor Green
}
finally {
    Pop-Location
    if (Test-Path -LiteralPath $LocalArchive) {
        Remove-Item -LiteralPath $LocalArchive -Force
    }
}
