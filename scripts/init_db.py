"""Initialize database schema and seed default admin.

Usage:
  python scripts/init_db.py
"""

import os
import sys

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from models import Admin, db


load_dotenv()
app = create_app(os.getenv("FLASK_ENV", "development"))

with app.app_context():
    db.create_all()

    username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    admin = Admin.query.filter_by(username=username).first()

    if admin is None:
        admin = Admin(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Created default admin: {username}")
    else:
        print("Default admin already exists")

    print("Database initialized successfully")
