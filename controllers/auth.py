"""Authentication: register (user/staff), login (all roles), logout."""

import re

from flask import (
    Blueprint, flash, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from models import db, StaffProfile, User
from utils import current_user, dashboard_url_for

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/")
def index():
    user = current_user()
    if user and not user.is_blacklisted:
        return redirect(dashboard_url_for(user))
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        role = request.form.get("role", "")
        contact = request.form.get("contact_number", "").strip()

        # ---- backend validation ----
        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not EMAIL_RE.match(email):
            errors.append("A valid email is required.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if role not in ("user", "staff"):
            errors.append("Please select a valid role.")
        if User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html", form=request.form)

        user = User(
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
        )
        if role == "staff":
            user.staff_profile = StaffProfile(contact_number=contact)
        db.session.add(user)
        db.session.commit()

        if role == "staff":
            flash("Registered! You can log in once the admin approves your account.", "info")
        else:
            flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form={})


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user is None or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        if user.is_blacklisted:
            flash("Your account has been blacklisted. Contact the admin.", "danger")
            return render_template("auth/login.html")

        if user.role == "staff":
            profile = user.staff_profile
            if profile is None or profile.approval_status == "Pending":
                flash("Your staff account is awaiting admin approval.", "warning")
                return render_template("auth/login.html")
            if profile.approval_status == "Rejected":
                flash("Your staff registration was rejected by the admin.", "danger")
                return render_template("auth/login.html")

        session.clear()
        session["user_id"] = user.id
        session["role"] = user.role
        flash(f"Welcome, {user.full_name}!", "success")
        return redirect(dashboard_url_for(user))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
