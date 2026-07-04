"""Trek Staff: dashboard, assigned trek management, participants, profile."""

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for
)
from werkzeug.security import generate_password_hash

from models import db, Booking, Trek
from utils import current_user, role_required

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


def _my_treks_query():
    return Trek.query.filter_by(staff_id=current_user().id)


def _owned_trek_or_404(trek_id):
    """Only the assigned staff member may manage a trek."""
    return Trek.query.filter_by(
        id=trek_id, staff_id=current_user().id
    ).first_or_404()


@staff_bp.route("/dashboard")
@role_required("staff")
def dashboard():
    treks = _my_treks_query().order_by(Trek.start_date).all()
    stats = {
        "assigned": len(treks),
        "participants": sum(t.booked_count for t in treks),
        "open": sum(1 for t in treks if t.status == "Open"),
    }
    return render_template("staff/dashboard.html", treks=treks, stats=stats)


@staff_bp.route("/treks")
@role_required("staff")
def treks():
    trek_list = _my_treks_query().order_by(Trek.start_date).all()
    return render_template("staff/treks.html", treks=trek_list)


@staff_bp.route("/treks/<int:trek_id>")
@role_required("staff")
def manage_trek(trek_id):
    trek = _owned_trek_or_404(trek_id)
    participants = trek.bookings.order_by(Booking.booking_date).all()
    return render_template(
        "staff/manage_trek.html", trek=trek, participants=participants
    )


@staff_bp.route("/treks/<int:trek_id>/update", methods=["POST"])
@role_required("staff")
def update_trek(trek_id):
    """Staff can update available slots and Open/Closed status."""
    trek = _owned_trek_or_404(trek_id)
    errors = []

    raw_slots = request.form.get("available_slots", "").strip()
    status = request.form.get("status", "").strip()

    slots = None
    try:
        slots = int(raw_slots)
        if slots < 0:
            raise ValueError
        if slots > trek.total_slots:
            errors.append(
                f"Available slots cannot exceed total slots ({trek.total_slots})."
            )
    except ValueError:
        errors.append("Available slots must be a non-negative whole number.")

    if status not in ("Open", "Closed"):
        errors.append("Status must be Open or Closed.")

    if trek.status in ("Started", "Completed"):
        errors.append(
            f"This trek is already {trek.status.lower()} and can no longer be edited."
        )

    if errors:
        for e in errors:
            flash(e, "danger")
    else:
        trek.available_slots = slots
        trek.status = status
        db.session.commit()
        flash("Trek slots and status updated.", "success")
    return redirect(url_for("staff.manage_trek", trek_id=trek.id))


@staff_bp.route("/treks/<int:trek_id>/mark/<string:action>", methods=["POST"])
@role_required("staff")
def mark_trek(trek_id, action):
    trek = _owned_trek_or_404(trek_id)
    if action == "started":
        if trek.status == "Completed":
            flash("A completed trek cannot be re-started.", "danger")
        else:
            trek.status = "Started"
            flash(f"'{trek.name}' marked as started.", "success")
    elif action == "completed":
        trek.status = "Completed"
        # record trekking history: active bookings become Completed
        for booking in trek.bookings.filter_by(status="Booked").all():
            booking.status = "Completed"
        flash(f"'{trek.name}' marked as completed.", "success")
    else:
        abort(404)
    db.session.commit()
    return redirect(url_for("staff.manage_trek", trek_id=trek.id))


@staff_bp.route("/profile", methods=["GET", "POST"])
@role_required("staff")
def profile():
    user = current_user()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        contact = request.form.get("contact_number", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if password and len(password) < 6:
            errors.append("New password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            user.full_name = full_name
            user.staff_profile.contact_number = contact
            if password:
                user.password_hash = generate_password_hash(password)
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("staff.profile"))
    return render_template("staff/profile.html")
