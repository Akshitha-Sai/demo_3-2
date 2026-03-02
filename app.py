import os

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_mail import Mail

from config import DevelopmentConfig, ProductionConfig, TestingConfig
from models import Admin, db
from routes.admin_routes import admin_bp
from routes.student_routes import student_bp
from utils import get_client_ip, is_blocked_ip, log_request


mail = Mail()


def create_app(config_name=None):
    load_dotenv()
    app = Flask(__name__)

    config_name = config_name or os.getenv("FLASK_ENV", "development")
    config_map = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    app.config.from_object(config_map.get(config_name, DevelopmentConfig))

    db.init_app(app)
    mail.init_app(app)

    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)

    @app.before_request
    def ddos_detection_middleware():
        endpoint = request.endpoint or ""
        if endpoint.startswith("static"):
            return None

        ip_address = get_client_ip(request)
        if is_blocked_ip(ip_address):
            flash("Your IP is temporarily blocked due to suspicious traffic.", "danger")
            return render_template("blocked.html"), 429

        user_id = session.get("user_id")
        request_count = log_request(ip_address, user_id=user_id, blocked=False)
        if request_count > app.config["REQUESTS_PER_MINUTE_THRESHOLD"]:
            log_request(ip_address, user_id=user_id, blocked=True)
            return render_template("blocked.html"), 429

        return None

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/traffic-data")
    def api_traffic_data_alias():
        return app.view_functions["admin.api_traffic_data"]()

    @app.route("/api/ddos-stats")
    def api_ddos_stats_alias():
        return app.view_functions["admin.api_ddos_stats"]()

    @app.route("/api/phishing-stats")
    def api_phishing_stats_alias():
        return app.view_functions["admin.api_phishing_stats"]()

    @app.cli.command("create-default-admin")
    def create_default_admin():
        username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
        password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
        if Admin.query.filter_by(username=username).first():
            print("Default admin already exists")
            return
        admin = Admin(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Created default admin '{username}'")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
