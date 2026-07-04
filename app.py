"""Trekking Management Application — entry point.

Creates the Flask app, initialises the SQLite database programmatically
(no manual DB creation), pre-seeds the admin superuser, and registers
the role-specific blueprints.
"""

from flask import Flask, render_template
from sqlalchemy.exc import SQLAlchemyError
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


def sync_legacy_schema():
    """Upgrade databases created before available_slots became a computed value.

    Older database files have a NOT NULL treks.available_slots column that the
    current model no longer fills in, which would break every trek INSERT.
    Dropping the legacy column programmatically keeps old DB files working.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "treks" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("treks")]
        if "available_slots" in columns:
            db.session.execute(text("ALTER TABLE treks DROP COLUMN available_slots"))
            db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "tma-mad1-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///trekking.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        sync_legacy_schema()
        seed_admin()

    from controllers.auth import auth_bp
    from controllers.admin import admin_bp
    from controllers.staff import staff_bp
    from controllers.user import user_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(user_bp)

    from utils import current_user

    @app.context_processor
    def inject_user():
        return {"user": current_user()}

    # ---- friendly error pages (no raw tracebacks for end users) ----

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(SQLAlchemyError)
    def database_error(e):
        db.session.rollback()
        app.logger.error("Database error: %s", e)
        return render_template(
            "errors/500.html",
            reason=(
                "Something went wrong while saving your changes. "
                "Please check your input and try again."
            ),
        ), 500

    @app.errorhandler(500)
    def internal_error(_e):
        return render_template("errors/500.html", reason=None), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
