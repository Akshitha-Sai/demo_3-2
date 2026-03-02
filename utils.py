import ipaddress
from datetime import datetime, timedelta
from urllib.parse import urlparse

from flask import current_app, flash
from flask_mail import Message

from models import AttackLog, db


LOCAL_IPS = {"127.0.0.1", "::1"}


def get_client_ip(request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"


def is_ip_address(hostname: str) -> bool:
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def analyze_phishing_url(url: str) -> str:
    parsed = urlparse(url if url.startswith(("http://", "https://")) else f"http://{url}")
    host = parsed.netloc.split(":")[0]

    suspicious_rules = [
        is_ip_address(host),
        "@" in url,
        host.count(".") >= 3,
        "-" in host,
    ]
    return "suspicious" if any(suspicious_rules) else "safe"


def send_registration_email(mail, recipient: str, event_title: str) -> None:
    if not current_app.config.get("MAIL_USERNAME"):
        flash("Email settings are not configured; confirmation email skipped.", "warning")
        return

    msg = Message(
        subject="Event Registration Confirmation",
        recipients=[recipient],
        body=(
            f"You are successfully registered for '{event_title}'.\n"
            "Thank you for using the Cloud-Based Event Management System."
        ),
    )
    mail.send(msg)


def log_request(ip_address: str, user_id=None, blocked=False) -> int:
    recent_count = (
        AttackLog.query.filter_by(ip_address=ip_address)
        .filter(AttackLog.timestamp >= datetime.utcnow() - timedelta(minutes=1))
        .count()
    )

    new_count = recent_count + 1
    log = AttackLog(
        user_id=user_id,
        ip_address=ip_address,
        request_count=new_count,
        is_blocked=blocked,
    )
    db.session.add(log)
    db.session.commit()
    return new_count


def is_blocked_ip(ip_address: str) -> bool:
    if ip_address in LOCAL_IPS:
        return False
    return (
        AttackLog.query.filter_by(ip_address=ip_address, is_blocked=True)
        .order_by(AttackLog.timestamp.desc())
        .first()
        is not None
    )
