# Cloud-Based Event Management System (Flask + PostgreSQL)

A complete Flask web app for event management with:
- Admin/student authentication
- Event CRUD and registration workflow
- DDoS request-rate detection + IP blocking logs
- Phishing URL heuristic scanner and logging
- PostgreSQL via SQLAlchemy ORM
- Chart.js live traffic graph
- Flask-Mail confirmation emails

## Project Structure

- `app.py` - App factory and middleware
- `config.py` - Development/production/testing config
- `models.py` - SQLAlchemy models
- `routes/admin_routes.py` - Admin pages + APIs
- `routes/student_routes.py` - Student auth + event registration
- `templates/` - Jinja UI
- `static/` - CSS/JS assets
- `scripts/init_db.py` - Database initialization and default admin seed

## PostgreSQL Setup

1. Create DB:
```sql
CREATE DATABASE eventdb;
```
2. Copy env file:
```bash
cp .env.example .env
```
3. Update `.env` with PostgreSQL credentials and mail settings.

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
python app.py
```

Visit `http://localhost:5000`.

## Default Accounts

- Admin username/password come from `.env` (`DEFAULT_ADMIN_USERNAME`, `DEFAULT_ADMIN_PASSWORD`).
- Students are created from `/student/register`.

## API Endpoints

- `GET /admin/api/traffic-data` - Last 60-minute request traffic
- `GET /admin/api/ddos-stats` - Request/blocked IP statistics
- `GET /admin/api/phishing-stats` - Safe vs suspicious URL totals

## Render Deployment Notes

- Add environment variables from `.env.example` in Render dashboard.
- Set `DATABASE_URL` to Render PostgreSQL internal URL.
- Start command:
```bash
gunicorn app:create_app\(\) --bind 0.0.0.0:$PORT
```
- App is HTTPS-ready behind Render proxy (`SESSION_COOKIE_SECURE` in production config).
