# Friendary 카페24 배포

권장 시작 사양은 DEV B(2코어, RAM 4GB), Ubuntu 24.04, PostgreSQL입니다.

## 1. 카페24 자동 구성 확인

```bash
systemctl status friendary --no-pager
systemctl is-active nginx postgresql
```

카페24가 `/opt/friendary`, `appuser`, PostgreSQL, Nginx, 무료 기본 도메인 HTTPS를 자동 구성합니다.

## 2. 기존 샘플 백업과 코드 배포

```bash
cp -a /opt/friendary /opt/friendary.fastapi-backup
tar -xf /root/friendary-deploy.tar -C /opt/friendary
chown -R appuser:appuser /opt/friendary
uv pip install --python /opt/friendary/.venv/bin/python -r /opt/friendary/requirements.txt
```

배포 압축 파일에는 `.env`, SQLite DB, Git 이력을 포함하지 않습니다.

## 3. PostgreSQL 연결

```bash
grep '^DATABASE_URL=' /etc/friendary/env | sed 's/=.*/=[보호됨]/'
```

카페24가 `/etc/friendary/env`에 `DATABASE_URL`을 자동 주입합니다. 실제 값을 출력하거나 Git에 저장하지 않습니다.

## 4. 운영 환경변수

`/etc/friendary/env`에 아래 운영 설정을 추가합니다. 기존 `DATABASE_URL`은 변경하지 않습니다.

```env
SECRET_KEY=REPLACE_WITH_A_LONG_RANDOM_VALUE
SESSION_COOKIE_SECURE=true
PREFERRED_URL_SCHEME=https
BEHIND_PROXY=true
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
```

OAuth 키와 Gmail 설정도 기존 로컬 `.env`에서 안전하게 옮깁니다. `.env`는 Git에 커밋하지 않습니다.

```bash
chmod 600 /etc/friendary/env
```

## 5. DB 스키마 생성

현재 앱은 시작 시 최신 모델의 테이블을 생성합니다. 최초 한 번 실행한 뒤 Alembic 현재 버전을 기록합니다.

```bash
sudo -u appuser /opt/friendary/.venv/bin/python -c "from wsgi import app; print('database initialized')"
sudo -u appuser /opt/friendary/.venv/bin/flask --app wsgi:app db stamp head
```

기존 SQLite 데이터가 필요하면 `friendary.db`를 삭제하지 말고 별도 이전 및 건수 검증을 먼저 수행합니다.

## 6. Gunicorn과 Nginx

```bash
cp -a /etc/systemd/system/friendary.service /etc/systemd/system/friendary.service.fastapi-backup
cp /opt/friendary/deploy/cafe24/friendary.service /etc/systemd/system/friendary.service
cp -a /etc/nginx/sites-enabled/friendary /root/friendary-nginx.fastapi-backup
sed -i 's#alias /opt/friendary/staticfiles/#alias /opt/friendary/pybo/static/#' /etc/nginx/sites-enabled/friendary
mv /var/www/cafe24-welcome/index.html /var/www/cafe24-welcome/index.html.fastapi-backup
nginx -t
systemctl daemon-reload
systemctl restart friendary
systemctl reload nginx
```

상태 확인:

```bash
systemctl status friendary --no-pager
journalctl -u friendary -n 100 --no-pager
```

## 7. 도메인과 HTTPS

카페24 기본 도메인은 HTTPS가 자동 적용됩니다. `friendary.com` 구매 후 DNS와 카페24 도메인 연결 관리에서 추가합니다.

```bash
# 카페24 도메인 연결 및 SSL 발급 절차를 사용합니다.
```

HTTPS가 정상 동작한 후 로그인, 게시글, 업로드, OAuth 콜백을 점검합니다.
