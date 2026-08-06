# 자동 가상환경 활성화 및 Flask 서버 실행 단축 스크립트
$venvPath = Join-Path $PSScriptRoot "venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
    Write-Host "가상환경(venv)이 자동으로 활성화되었습니다." -ForegroundColor Green
} else {
    Write-Host "가상환경 경로를 찾을 수 없어 기본 환경으로 계속합니다." -ForegroundColor Yellow
}

$env:FLASK_APP = "pybo"
$env:FLASK_DEBUG = "true"

Write-Host "Flask 서버를 시작합니다... (http://127.0.0.1:5000)" -ForegroundColor Cyan
flask run
