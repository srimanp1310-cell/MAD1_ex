"""Auth helpers: session-based login and role-based access control.

Core requirements are implemented with plain Flask sessions (no JS,
no Flask-Login) as permitted by the project statement.
"""

from functools import wraps

from flask import abort, flash, redirect, session, url_for

from models import User


def current_user():
    """Return the logged-in User object, or None."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return User.query.get(user_id)


def login_required(view):
    """Redirect to login if no user is in the session."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles):
    """Restrict a view to the given roles (e.g. @role_required('admin'))."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login"))
            if user.is_blacklisted:
                session.clear()
                flash("Your account has been blacklisted. Contact the admin.", "danger")
                return redirect(url_for("auth.login"))
            if user.role not in roles:
                abort(403)
            # unapproved staff must not reach any staff page
            if user.role == "staff" and (
                user.staff_profile is None
                or user.staff_profile.approval_status != "Approved"
            ):
                session.clear()
                flash("Your staff account is not approved yet.", "warning")
                return redirect(url_for("auth.login"))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def dashboard_url_for(user):
    """Role-specific dashboard endpoint for redirects after login."""
    return {
        "admin": url_for("admin.dashboard"),
        "staff": url_for("staff.dashboard"),
        "user": url_for("user.dashboard"),
    }[user.role]
