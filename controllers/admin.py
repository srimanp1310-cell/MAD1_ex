"""Admin: dashboard stats, trek CRUD, staff approval/blacklist,
user management, search, and booking records."""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import (
    db, Booking, StaffProfile, Trek, User,
    DIFFICULTIES, TREK_STATUSES,
)
from utils import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ---------------------------------------------------------------- dashboard

@admin_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    stats = {
        "treks": Trek.query.count(),
        "users": User.query.filter_by(role="user").count(),
        "staff": User.query.filter_by(role="staff").count(),
        "bookings": Booking.query.count(),
        "pending_staff": StaffProfile.query.filter_by(approval_status="Pending").count(),
    }
    recent_bookings = (
        Booking.query.order_by(Booking.booking_date.desc()).limit(5).all()
    )
    return render_template(
        "admin/dashboard.html", stats=stats, recent_bookings=recent_bookings
    )


# ------------------------------------------------------------------- treks

def _approved_staff():
    """Approved, non-blacklisted staff selectable for trek assignment."""
    return (
        User.query.join(StaffProfile)
        .filter(
            User.role == "staff",
            User.is_blacklisted.is_(False),
            StaffProfile.approval_status == "Approved",
        )
        .order_by(User.full_name)
        .all()
    )


def _validate_trek_form(form):
    """Backend validation for add/edit trek. Returns (data, errors)."""
    errors = []
    data = {
        "name": form.get("name", "").strip(),
        "location": form.get("location", "").strip(),
        "difficulty": form.get("difficulty", ""),
        "status": form.get("status", "Pending"),
        "description": form.get("description", "").strip(),
    }

    if not data["name"]:
        errors.append("Trek name is required.")
    if not data["location"]:
        errors.append("Location is required.")
    if data["difficulty"] not in DIFFICULTIES:
        errors.append("Please select a valid difficulty.")
    if data["status"] not in TREK_STATUSES:
        errors.append("Please select a valid status.")

    for field, label in (("duration_days", "Duration"), ("total_slots", "Slots")):
        raw = form.get(field, "").strip()
        try:
            value = int(raw)
            if value <= 0:
                raise ValueError
            data[field] = value
        except ValueError:
            errors.append(f"{label} must be a positive whole number.")

    for field, label in (("start_date", "Start date"), ("end_date", "End date")):
        raw = form.get(field, "").strip()
        if raw:
            try:
                data[field] = datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append(f"{label} is not a valid date.")
        else:
            data[field] = None

    if data.get("start_date") and data.get("end_date") and data["end_date"] < data["start_date"]:
        errors.append("End date cannot be before start date.")

    staff_id = form.get("staff_id", "")
    if staff_id:
        staff = next((s for s in _approved_staff() if str(s.id) == staff_id), None)
        if staff is None:
            errors.append("Selected staff member is not valid.")
        else:
            data["staff_id"] = staff.id
    else:
        data["staff_id"] = None

    return data, errors


@admin_bp.route("/treks")
@role_required("admin")
def treks():
    q = request.args.get("q", "").strip()
    query = Trek.query
    if q:
        if q.isdigit():
            query = query.filter(
                db.or_(Trek.id == int(q), Trek.name.ilike(f"%{q}%"))
            )
        else:
            query = query.filter(Trek.name.ilike(f"%{q}%"))
    trek_list = query.order_by(Trek.id).all()
    return render_template("admin/treks.html", treks=trek_list, q=q)


@admin_bp.route("/treks/add", methods=["GET", "POST"])
@role_required("admin")
def add_trek():
    if request.method == "POST":
        data, errors = _validate_trek_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            trek = Trek(available_slots=data["total_slots"], **data)
            db.session.add(trek)
            db.session.commit()
            flash(f"Trek '{trek.name}' created.", "success")
            return redirect(url_for("admin.treks"))
    return render_template(
        "admin/trek_form.html",
        trek=None, form=request.form, staff_options=_approved_staff(),
        difficulties=DIFFICULTIES, statuses=TREK_STATUSES,
    )


@admin_bp.route("/treks/<int:trek_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    if request.method == "POST":
        data, errors = _validate_trek_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            booked = trek.booked_count
            if data["total_slots"] < booked:
                flash(
                    f"Cannot reduce slots below current active bookings ({booked}).",
                    "danger",
                )
            else:
                for key, value in data.items():
                    setattr(trek, key, value)
                trek.available_slots = data["total_slots"] - booked
                db.session.commit()
                flash(f"Trek '{trek.name}' updated.", "success")
                return redirect(url_for("admin.treks"))
    return render_template(
        "admin/trek_form.html",
        trek=trek, form=request.form, staff_options=_approved_staff(),
        difficulties=DIFFICULTIES, statuses=TREK_STATUSES,
    )


@admin_bp.route("/treks/<int:trek_id>/delete", methods=["POST"])
@role_required("admin")
def delete_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    if trek.bookings.count():
        flash(
            "This trek has bookings and cannot be deleted (history must be kept). "
            "Set its status to Closed or Completed instead.",
            "warning",
        )
    else:
        db.session.delete(trek)
        db.session.commit()
        flash(f"Trek '{trek.name}' removed.", "success")
    return redirect(url_for("admin.treks"))


# ------------------------------------------------------------------- staff

@admin_bp.route("/staff")
@role_required("admin")
def staff():
    tab = request.args.get("tab", "pending")
    base = User.query.join(StaffProfile).filter(User.role == "staff")
    lists = {
        "pending": base.filter(StaffProfile.approval_status == "Pending",
                               User.is_blacklisted.is_(False)),
        "approved": base.filter(StaffProfile.approval_status == "Approved",
                                User.is_blacklisted.is_(False)),
        "blacklisted": base.filter(db.or_(User.is_blacklisted.is_(True),
                                          StaffProfile.approval_status == "Rejected")),
    }
    counts = {name: q.count() for name, q in lists.items()}
    if tab not in lists:
        tab = "pending"
    staff_list = lists[tab].order_by(User.id).all()
    return render_template(
        "admin/staff.html", staff_list=staff_list, tab=tab, counts=counts
    )


@admin_bp.route("/staff/<int:user_id>/approve", methods=["POST"])
@role_required("admin")
def approve_staff(user_id):
    user = User.query.filter_by(id=user_id, role="staff").first_or_404()
    user.staff_profile.approval_status = "Approved"
    db.session.commit()
    flash(f"{user.full_name} approved as trek staff.", "success")
    return redirect(url_for("admin.staff"))


@admin_bp.route("/staff/<int:user_id>/reject", methods=["POST"])
@role_required("admin")
def reject_staff(user_id):
    user = User.query.filter_by(id=user_id, role="staff").first_or_404()
    user.staff_profile.approval_status = "Rejected"
    db.session.commit()
    flash(f"{user.full_name}'s staff registration rejected.", "info")
    return redirect(url_for("admin.staff"))


# ------------------------------------------------------------------- users

@admin_bp.route("/users")
@role_required("admin")
def users():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(role="user")
    if q:
        if q.isdigit():
            query = query.filter(
                db.or_(User.id == int(q), User.full_name.ilike(f"%{q}%"))
            )
        else:
            query = query.filter(User.full_name.ilike(f"%{q}%"))
    return render_template("admin/users.html", users=query.order_by(User.id).all(), q=q)


@admin_bp.route("/accounts/<int:user_id>/toggle-blacklist", methods=["POST"])
@role_required("admin")
def toggle_blacklist(user_id):
    account = User.query.get_or_404(user_id)
    if account.role == "admin":
        flash("The admin account cannot be blacklisted.", "danger")
        return redirect(request.referrer or url_for("admin.dashboard"))
    account.is_blacklisted = not account.is_blacklisted
    db.session.commit()
    state = "blacklisted" if account.is_blacklisted else "re-activated"
    flash(f"{account.full_name} has been {state}.", "info")
    return redirect(request.referrer or url_for("admin.dashboard"))


# ---------------------------------------------------------------- bookings

@admin_bp.route("/bookings")
@role_required("admin")
def bookings():
    records = Booking.query.order_by(Booking.booking_date.desc()).all()
    return render_template("admin/bookings.html", bookings=records)


# ------------------------------------------------------------------ search

@admin_bp.route("/search")
@role_required("admin")
def search():
    q = request.args.get("q", "").strip()
    results = {"treks": [], "users": [], "staff": []}
    if q:
        if q.isdigit():
            id_filter = int(q)
            results["treks"] = Trek.query.filter(
                db.or_(Trek.id == id_filter, Trek.name.ilike(f"%{q}%"))
            ).all()
            people = User.query.filter(
                db.or_(User.id == id_filter, User.full_name.ilike(f"%{q}%"))
            ).all()
        else:
            results["treks"] = Trek.query.filter(Trek.name.ilike(f"%{q}%")).all()
            people = User.query.filter(User.full_name.ilike(f"%{q}%")).all()
        results["users"] = [p for p in people if p.role == "user"]
        results["staff"] = [p for p in people if p.role == "staff"]
    return render_template("admin/search.html", q=q, results=results)
