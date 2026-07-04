"""Trekking Management Application — entry point.

Creates the Flask app, initialises the SQLite database programmatically
(no manual DB creation), and pre-seeds the admin superuser.
"""

from flask import Flask
from werkzeug.security import generate_password_hash

from models import db, User

ADMIN_EMAIL = "admin@tma.com"
ADMIN_PASSWORD = "admin123"  # demo credential for the course project


def seed_admin():
    """Pre-create the admin superuser programmatically (no registration)."""
    if not User.query.filter_by(email=ADMIN_EMAIL).first():
        admin = User(
            full_name="Admin",
            email=ADMIN_EMAIL,
            password_hash=generate_password_hash(ADMIN_PASSWORD),
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "tma-mad1-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///trekking.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_admin()

    return app


app = create_app()


@app.route("/")
def index():
    return "Trekking Management Application — setup OK"


if __name__ == "__main__":
    app.run(debug=True)
