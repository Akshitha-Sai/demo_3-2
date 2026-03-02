from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from models import Event, Registration, User, db
from utils import send_registration_email


student_bp = Blueprint("student", __name__, url_prefix="/student")


def student_required():
    return session.get("user_id") is not None and session.get("role") == "student"


@student_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if User.query.filter_by(email=request.form["email"]).first():
            flash("Email already exists.", "danger")
            return redirect(url_for("student.register"))

        user = User(
            name=request.form["name"],
            email=request.form["email"],
            role="student",
        )
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        flash("Registration complete. Please login.", "success")
        return redirect(url_for("student.login"))
    return render_template("student/register.html")


@student_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email, role="student").first()
        if user and user.check_password(password):
            session.clear()
            session["user_id"] = user.id
            session["role"] = "student"
            return redirect(url_for("student.events"))
        flash("Invalid credentials.", "danger")
    return render_template("student/login.html")


@student_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("index"))


@student_bp.route("/events")
def events():
    if not student_required():
        return redirect(url_for("student.login"))

    user_id = session["user_id"]
    events_list = Event.query.order_by(Event.date.asc(), Event.time.asc()).all()
    registered_event_ids = {
        registration.event_id
        for registration in Registration.query.filter_by(user_id=user_id).all()
    }
    return render_template(
        "student/events.html",
        events=events_list,
        registered_event_ids=registered_event_ids,
        today=datetime.utcnow().date(),
    )


@student_bp.route("/events/<int:event_id>/register", methods=["POST"])
def register_event(event_id):
    if not student_required():
        return redirect(url_for("student.login"))

    event = Event.query.get_or_404(event_id)
    user_id = session["user_id"]

    if event.deadline < datetime.utcnow().date():
        flash("Registration deadline has passed.", "warning")
        return redirect(url_for("student.events"))

    existing = Registration.query.filter_by(user_id=user_id, event_id=event_id).first()
    if existing:
        flash("You are already registered for this event.", "info")
        return redirect(url_for("student.events"))

    registration = Registration(user_id=user_id, event_id=event_id)
    db.session.add(registration)
    db.session.commit()

    user = User.query.get(user_id)
    send_registration_email(current_app.extensions["mail"], user.email, event.title)

    flash("Registered successfully.", "success")
    return redirect(url_for("student.events"))
