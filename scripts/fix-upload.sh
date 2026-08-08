#!/bin/bash
# ──────────────────────────────────────────────────
# Friendary 업로드 문제 긴급 수정 스크립트
# SSH 접속 후 root 권한으로 실행해 주세요:
#   bash /tmp/fix-upload.sh
# ──────────────────────────────────────────────────
set -eu

APP_PATH="/opt/friendary"
NGINX_CONF="/etc/nginx/sites-enabled/friendary"
UPLOADS_DIR="$APP_PATH/pybo/static/uploads"

echo "=== [1/4] uploads 디렉토리 확인 ==="
mkdir -p "$UPLOADS_DIR"
chown appuser:www-data "$UPLOADS_DIR"
chmod 775 "$UPLOADS_DIR"
echo "  ✅ $UPLOADS_DIR -> appuser:www-data (775)"
ls -la "$UPLOADS_DIR/" | head -5

echo ""
echo "=== [2/4] Nginx client_max_body_size 확인 ==="
if grep -q 'client_max_body_size' "$NGINX_CONF" 2>/dev/null; then
    echo "  ✅ 이미 설정되어 있습니다:"
    grep 'client_max_body_size' "$NGINX_CONF"
else
    echo "  ⚠️  client_max_body_size 미설정 → 10M 추가"
    # server 블록의 첫 번째 줄 뒤에 삽입
    sed -i '/server_name/a \    client_max_body_size 10M;' "$NGINX_CONF"
    echo "  ✅ 추가 완료"
    grep 'client_max_body_size' "$NGINX_CONF"
fi

echo ""
echo "=== [3/4] Nginx 설정 검증 및 리로드 ==="
nginx -t && systemctl reload nginx
echo "  ✅ Nginx 리로드 완료"

echo ""
echo "=== [4/4] Gunicorn 최근 에러 로그 확인 ==="
journalctl -u friendary -n 20 --no-pager 2>/dev/null | grep -i "error\|413\|permission\|denied" || echo "  (최근 관련 에러 없음)"

echo ""
echo "=========================================="
echo "✅ 업로드 문제 수정 완료!"
echo "  - uploads 디렉토리 권한: appuser:www-data (775)"
echo "  - Nginx client_max_body_size: 10M"
echo "=========================================="
