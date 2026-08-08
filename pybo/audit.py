"""Append-only security audit logging."""

import hashlib
import json

from flask import current_app, request, session


def audit_event(event_type, details=None, user_id=None):
    from pybo import db
    from pybo.models import SecurityAuditEvent

    address = request.remote_addr or "unknown"
    event = SecurityAuditEvent(
        user_id=user_id or session.get("user_id"),
        event_type=event_type[:60],
        ip_hash=hashlib.sha256(address.encode()).hexdigest(),
        details=json.dumps(details or {}, ensure_ascii=False, default=str)[:2000],
    )
    try:
        db.session.add(event)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Security audit event could not be persisted")

