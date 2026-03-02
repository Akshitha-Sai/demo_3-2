from datetime import datetime, timedelta

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import func

from models import Admin, AttackLog, Event, PhishingURL, Registration, User, db
from utils import analyze_phishing_url


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required():
    return session.get("admin_id") is not None


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session.clear()
            session["admin_id"] = admin.id
            session["role"] = "admin"
            return redirect(url_for("admin.dashboard"))
        flash("Invalid admin credentials", "danger")
    return render_template("admin/login.html")


@admin_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("index"))


@admin_bp.route("/dashboard")
def dashboard():
    if not admin_required():
        return redirect(url_for("admin.login"))

    total_events = Event.query.count()
    total_users = User.query.count()
    total_registrations = Registration.query.count()
    blocked_ips = AttackLog.query.filter_by(is_blocked=True).count()

    recent_attack_logs = AttackLog.query.order_by(AttackLog.timestamp.desc()).limit(20).all()
    recent_phishing = PhishingURL.query.order_by(PhishingURL.checked_at.desc()).limit(20).all()
    events = Event.query.order_by(Event.date.asc(), Event.time.asc()).all()

    return render_template(
        "admin/dashboard.html",
        total_events=total_events,
        total_users=total_users,
        total_registrations=total_registrations,
        blocked_ips=blocked_ips,
        recent_attack_logs=recent_attack_logs,
        recent_phishing=recent_phishing,
        events=events,
    )


@admin_bp.route("/events/create", methods=["POST"])
def create_event():
    if not admin_required():
        return redirect(url_for("admin.login"))

    event = Event(
        title=request.form["title"],
        description=request.form["description"],
        date=datetime.strptime(request.form["date"], "%Y-%m-%d").date(),
        time=datetime.strptime(request.form["time"], "%H:%M").time(),
        venue=request.form["venue"],
        deadline=datetime.strptime(request.form["deadline"], "%Y-%m-%d").date(),
        created_by=session["admin_id"],
    )
    db.session.add(event)
    db.session.commit()
    flash("Event created successfully.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/events/<int:event_id>/update", methods=["POST"])
def update_event(event_id):
    if not admin_required():
        return redirect(url_for("admin.login"))

    event = Event.query.get_or_404(event_id)
    event.title = request.form["title"]
    event.description = request.form["description"]
    event.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
    event.time = datetime.strptime(request.form["time"], "%H:%M").time()
    event.venue = request.form["venue"]
    event.deadline = datetime.strptime(request.form["deadline"], "%Y-%m-%d").date()
    db.session.commit()
    flash("Event updated successfully.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/events/<int:event_id>/delete", methods=["POST"])
def delete_event(event_id):
    if not admin_required():
        return redirect(url_for("admin.login"))

    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted successfully.", "warning")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/registrations")
def registrations():
    if not admin_required():
        return redirect(url_for("admin.login"))

    rows = (
        db.session.query(Registration, User, Event)
        .join(User, Registration.user_id == User.id)
        .join(Event, Registration.event_id == Event.id)
        .order_by(Registration.registered_at.desc())
        .all()
    )
    return render_template("admin/registrations.html", rows=rows)


@admin_bp.route("/unblock-ip", methods=["POST"])
def unblock_ip():
    if not admin_required():
        return redirect(url_for("admin.login"))

    ip = request.form.get("ip_address", "").strip()
    if not ip:
        flash("IP is required.", "danger")
        return redirect(url_for("admin.dashboard"))

    blocked_entries = AttackLog.query.filter_by(ip_address=ip, is_blocked=True).all()
    for row in blocked_entries:
        row.is_blocked = False
    db.session.commit()
    flash(f"IP {ip} unblocked.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/phishing-check", methods=["POST"])
def phishing_check():
    if not admin_required():
        return redirect(url_for("admin.login"))

    url = request.form.get("url", "").strip()
    if not url:
        flash("URL is required", "danger")
        return redirect(url_for("admin.dashboard"))

    status = analyze_phishing_url(url)
    row = PhishingURL(url=url, detected_as=status)
    db.session.add(row)
    db.session.commit()
    flash(f"URL analyzed as {status}.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/api/traffic-data")
def api_traffic_data():
    if not admin_required():
        return jsonify({"error": "Unauthorized"}), 401

    one_hour_ago = datetime.utcnow() - timedelta(minutes=60)
    data = (
        db.session.query(
            func.date_trunc("minute", AttackLog.timestamp).label("minute"),
            func.count(AttackLog.id).label("requests"),
        )
        .filter(AttackLog.timestamp >= one_hour_ago)
        .group_by("minute")
        .order_by("minute")
        .all()
    )
    return jsonify(
        {
            "labels": [row.minute.strftime("%H:%M") for row in data],
            "values": [row.requests for row in data],
        }
    )


@admin_bp.route("/api/ddos-stats")
def api_ddos_stats():
    if not admin_required():
        return jsonify({"error": "Unauthorized"}), 401

    total_requests = AttackLog.query.count()
    blocked_requests = AttackLog.query.filter_by(is_blocked=True).count()
    unique_ips = db.session.query(AttackLog.ip_address).distinct().count()
    blocked_ips = (
        db.session.query(AttackLog.ip_address)
        .filter_by(is_blocked=True)
        .distinct()
        .count()
    )
    return jsonify(
        {
            "total_requests": total_requests,
            "blocked_requests": blocked_requests,
            "unique_ips": unique_ips,
            "blocked_ips": blocked_ips,
            "threshold": current_app.config["REQUESTS_PER_MINUTE_THRESHOLD"],
        }
    )


@admin_bp.route("/api/phishing-stats")
def api_phishing_stats():
    if not admin_required():
        return jsonify({"error": "Unauthorized"}), 401

    safe_count = PhishingURL.query.filter_by(detected_as="safe").count()
    suspicious_count = PhishingURL.query.filter_by(detected_as="suspicious").count()
    return jsonify({"safe": safe_count, "suspicious": suspicious_count})
