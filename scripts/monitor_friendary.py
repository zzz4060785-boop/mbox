"""Check Friendary availability and notify once on outage and recovery."""

from __future__ import annotations

import json
import os
import smtplib
import ssl
import sys
import os.path
import shutil
import base64
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


MONITOR_URL = os.getenv("MONITOR_URL", "https://zzz8247.mycafe24.com/healthz").strip()
STATE_FILE = Path(os.getenv("MONITOR_STATE_FILE", "/var/lib/friendary-monitor/state.json"))
FAILURE_THRESHOLD = max(1, int(os.getenv("MONITOR_FAILURE_THRESHOLD", "3")))
EVENT_FILE = Path(os.getenv("INCIDENT_EVENT_FILE", "/var/lib/friendary-monitor/events.jsonl"))
BACKUP_DIR = Path(os.getenv("DB_BACKUP_DIR", "/opt/friendary/db-backups"))


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"failures": 0, "alerted": False}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state), encoding="utf-8")
    temporary.replace(STATE_FILE)


def probe() -> tuple[bool, str]:
    request = Request(
        MONITOR_URL,
        headers={"User-Agent": "Friendary-Monitor/1.0", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            if response.status != 200:
                return False, f"HTTP {response.status}"
            payload = json.loads(body)
            if payload.get("status") != "ok":
                return False, f"unexpected response: {body[:200]}"
            return True, "HTTP 200, database OK"
    except HTTPError as error:
        return False, f"HTTP {error.code}"
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
        return False, f"{type(error).__name__}: {error}"


def send_webhook(message: str) -> bool:
    webhook_url = os.getenv("MONITOR_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return False
    payload = json.dumps({"text": message, "content": message}).encode("utf-8")
    request = Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Friendary-Monitor/1.0"},
        method="POST",
    )
    with urlopen(request, timeout=15):
        return True


def send_email(subject: str, message: str) -> bool:
    recipient = os.getenv("MONITOR_EMAIL_TO", "").strip()
    host = os.getenv("SMTP_HOST", "").strip()
    sender = os.getenv("SMTP_FROM_EMAIL", "").strip()
    if not all((recipient, host, sender)):
        return send_gmail_oauth(subject, message, recipient)
    mail = EmailMessage()
    mail["Subject"] = subject
    mail["From"] = sender
    mail["To"] = recipient
    mail.set_content(message)
    port = int(os.getenv("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        username = os.getenv("SMTP_USERNAME", "").strip()
        if username:
            smtp.login(username, os.getenv("SMTP_PASSWORD", ""))
        smtp.send_message(mail)
    return True


def send_gmail_oauth(subject: str, message: str, recipient: str) -> bool:
    """Reuse the administrator Gmail connection already stored by Friendary."""
    if not recipient:
        return False
    from pybo import create_app, db
    from pybo.crypto import decrypt_secret
    from pybo.models import GmailCredential

    app = create_app()
    with app.app_context():
        admin_email = app.config["GMAIL_ADMIN_EMAIL"].lower()
        credential = GmailCredential.query.filter_by(email=admin_email).first()
        if not credential or not app.config.get("GMAIL_CLIENT_ID") or not app.config.get("GMAIL_CLIENT_SECRET"):
            return False
        refresh_token = decrypt_secret(app.config, credential.refresh_token)
        token_request = Request(
            "https://oauth2.googleapis.com/token",
            data=urlencode(
                {
                    "client_id": app.config["GMAIL_CLIENT_ID"],
                    "client_secret": app.config["GMAIL_CLIENT_SECRET"],
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(token_request, timeout=15) as response:
            access_token = json.loads(response.read())["access_token"]
        mail = EmailMessage()
        mail["Subject"] = subject
        mail["From"] = admin_email
        mail["To"] = recipient
        mail.set_content(message)
        raw_message = base64.urlsafe_b64encode(mail.as_bytes()).decode("ascii")
        send_request = Request(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            data=json.dumps({"raw": raw_message}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(send_request, timeout=15):
            return True


def notify(subject: str, detail: str) -> None:
    timestamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    message = f"{subject}\n시간: {timestamp}\n대상: {MONITOR_URL}\n상세: {detail}"
    delivered = False
    errors = []
    for sender in (lambda: send_webhook(message), lambda: send_email(subject, message)):
        try:
            delivered = sender() or delivered
        except Exception as error:  # Keep the second notification channel available.
            errors.append(f"{type(error).__name__}: {error}")
    if not delivered:
        raise RuntimeError("No monitor notification was delivered" + (f" ({'; '.join(errors)})" if errors else ""))


def system_problems() -> list[str]:
    problems = []
    try:
        load_one = os.getloadavg()[0]
        cpu_percent = load_one / max(1, os.cpu_count() or 1) * 100
        if cpu_percent >= float(os.getenv("MONITOR_CPU_PERCENT", "90")):
            problems.append(f"CPU 부하 {cpu_percent:.1f}%")
    except (AttributeError, OSError):
        pass

    try:
        memory = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, value = line.split(":", 1)
            memory[key] = int(value.strip().split()[0])
        used_percent = (1 - memory["MemAvailable"] / memory["MemTotal"]) * 100
        if used_percent >= float(os.getenv("MONITOR_MEMORY_PERCENT", "90")):
            problems.append(f"RAM 사용률 {used_percent:.1f}%")
    except (OSError, KeyError, ValueError):
        pass

    disk = shutil.disk_usage("/")
    disk_percent = disk.used / disk.total * 100
    if disk_percent >= float(os.getenv("MONITOR_DISK_PERCENT", "85")):
        problems.append(f"디스크 사용률 {disk_percent:.1f}%")

    backups = list(BACKUP_DIR.glob("friendary-*.dump"))
    if not backups:
        problems.append("DB 백업 파일 없음")
    else:
        newest = max(path.stat().st_mtime for path in backups)
        age_hours = (datetime.now().timestamp() - newest) / 3600
        if age_hours > float(os.getenv("MONITOR_BACKUP_MAX_AGE_HOURS", "26")):
            problems.append(f"마지막 DB 백업이 {age_hours:.1f}시간 전")
    return problems


def consume_incident_events() -> list[str]:
    try:
        lines = EVENT_FILE.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    if not lines:
        return []
    EVENT_FILE.write_text("", encoding="utf-8")
    events = []
    for line in lines[-50:]:
        try:
            event = json.loads(line)
            events.append(f"{event.get('occurred_at', '')} {event.get('type', 'incident')}: {event.get('detail', '')}")
        except json.JSONDecodeError:
            events.append(line[:500])
    return events


def main() -> int:
    if "--test-alert" in sys.argv[1:]:
        notify("[시험] Friendary 서버 감시 알림", "감시자 메일 발송이 정상적으로 연결되었습니다")
        print("test alert delivered")
        return 0
    state = load_state()
    healthy, detail = probe()
    problems = system_problems()
    events = consume_incident_events()
    previous_problems = state.get("system_problems", [])
    if problems and problems != previous_problems:
        notify("[경고] Friendary 서버 자원/백업 이상", "\n".join(problems))
    elif not problems and previous_problems:
        notify("[복구] Friendary 서버 자원/백업 정상화", "모든 지표가 정상 범위입니다")
    if events:
        notify("[보안/오류] Friendary 사건 감지", "\n".join(events))
    state["system_problems"] = problems
    if healthy:
        was_alerted = bool(state.get("alerted"))
        state.update(failures=0, alerted=False, last_result=detail)
        save_state(state)
        if was_alerted:
            notify("[복구] Friendary 서버가 정상화되었습니다", detail)
        print(f"healthy: {detail}")
        return 0

    failures = int(state.get("failures", 0)) + 1
    alerted = bool(state.get("alerted"))
    state.update(failures=failures, last_result=detail)
    save_state(state)
    if failures >= FAILURE_THRESHOLD and not alerted:
        notify("[장애] Friendary 서버 점검 실패", f"{failures}회 연속 실패; {detail}")
        state["alerted"] = True
        save_state(state)
    print(f"unhealthy ({failures}/{FAILURE_THRESHOLD}): {detail}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
