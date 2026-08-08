"""Application-wide HTTP security helpers."""

from functools import wraps
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path

from flask import abort, current_app, g, jsonify, request, session
from flask.signals import got_request_exception


UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _incident_event(event_type, detail):
    event_file = Path(current_app.config.get("INCIDENT_EVENT_FILE", "/var/lib/friendary-monitor/events.jsonl"))
    event = {
        "type": event_type,
        "detail": detail,
        "occurred_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    try:
        event_file.parent.mkdir(parents=True, exist_ok=True)
        with event_file.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:
        current_app.logger.exception("Unable to write incident event")


def _ip_hash(address):
    secret = current_app.config["SECRET_KEY"].encode("utf-8")
    return hmac.new(secret, address.encode("utf-8"), hashlib.sha256).hexdigest()


def record_unknown_login_attempt():
    """Count nonexistent-account probes and permanently block their source at 20."""
    from sqlalchemy.exc import IntegrityError
    from pybo import db
    from pybo.models import SecurityIPBlock

    address = request.remote_addr or "unknown"
    address_hash = _ip_hash(address)
    now = datetime.utcnow()
    window_start = now - timedelta(hours=24)
    record = SecurityIPBlock.query.filter_by(ip_hash=address_hash).with_for_update().first()
    if record is None:
        record = SecurityIPBlock(
            ip_hash=address_hash,
            unknown_login_attempts=0,
            window_started_at=now,
            last_attempt_at=now,
        )
        db.session.add(record)
    elif record.blocked_at is None and record.window_started_at < window_start:
        record.unknown_login_attempts = 0
        record.window_started_at = now

    record.unknown_login_attempts += 1
    record.last_attempt_at = now
    count = record.unknown_login_attempts
    if count >= 20 and record.blocked_at is None:
        record.blocked_at = now
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return 0

    if count == 10:
        _incident_event("intrusion_warning", f"IP {address}에서 미가입 아이디 로그인 시도 10회")
    elif count == 20:
        _incident_event("ip_blocked", f"IP {address}에서 미가입 아이디 로그인 시도 20회; 사이트 접근 차단")
    return count


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def csp_nonce():
    return g.csp_nonce


def _csrf_protect():
    if request.method not in UNSAFE_METHODS:
        return None
    expected = session.get("_csrf_token")
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        if request.path.startswith("/api/") or request.is_json:
            return jsonify(success=False, message="보안 토큰이 없거나 만료되었습니다."), 400
        abort(400, description="보안 토큰이 없거나 만료되었습니다.")
    return None


def rate_limit(limit=10, window=60, scope=None):
    """Small per-process limiter for sensitive endpoints.

    Production deployments should additionally enforce limits at the reverse proxy.
    """
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if request.method not in UNSAFE_METHODS:
                return view(*args, **kwargs)
            from sqlalchemy.exc import IntegrityError
            from pybo import db
            from pybo.models import SecurityRateLimit

            # ProxyFix has already normalized remote_addr when BEHIND_PROXY is enabled.
            address = request.remote_addr or "unknown"
            key_hash = hashlib.sha256(f"{scope or request.endpoint}:{address}".encode()).hexdigest()
            window_start = int(time.time()) // window * window
            record = SecurityRateLimit.query.filter_by(
                key_hash=key_hash, window_start=window_start
            ).with_for_update().first()
            if record is None:
                record = SecurityRateLimit(key_hash=key_hash, window_start=window_start, count=0)
                db.session.add(record)
            if record.count >= limit:
                db.session.rollback()
                return jsonify(success=False, message="요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."), 429
            record.count += 1
            try:
                # Bound table growth; old windows have no security value.
                SecurityRateLimit.query.filter(
                    SecurityRateLimit.window_start < window_start - (window * 10)
                ).delete(synchronize_session=False)
                db.session.commit()
            except IntegrityError:
                # A concurrent first request created the same window row. Fail closed.
                db.session.rollback()
                return jsonify(success=False, message="잠시 후 다시 시도해 주세요."), 429
            return view(*args, **kwargs)
        return wrapped
    return decorator


def init_security(app):
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.jinja_env.globals["csp_nonce"] = csp_nonce

    @app.before_request
    def prepare_security_context():
        g.csp_nonce = secrets.token_urlsafe(18)

        # The health probe must remain reachable so outages can still be diagnosed.
        if request.path == "/healthz" or not current_app.config.get("IP_BLOCKING_ENABLED", False):
            return None
        from pybo.models import SecurityIPBlock
        blocked = SecurityIPBlock.query.filter_by(
            ip_hash=_ip_hash(request.remote_addr or "unknown")
        ).filter(SecurityIPBlock.blocked_at.isnot(None)).first()
        if blocked:
            return jsonify(success=False, message="Access denied"), 403

    def capture_unhandled_exception(sender, exception, **extra):
        _incident_event(
            "flask_error",
            f"{type(exception).__name__} at {request.method} {request.path}",
        )

    got_request_exception.connect(capture_unhandled_exception, app, weak=False)

    app.before_request(_csrf_protect)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(self)")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self' https: data: blob:; "
            f"script-src 'self' https://cdn.iamport.kr https://cdn.portone.io 'nonce-{g.csp_nonce}'; script-src-attr 'none'; "
            "style-src 'self' 'unsafe-inline' https:; object-src 'none'; base-uri 'self'; frame-ancestors 'self'",
        )
        if request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
