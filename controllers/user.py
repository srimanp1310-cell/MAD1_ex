"""User (Trekker): dashboard, browse & book treks, my bookings, profile."""

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for
)
from werkzeug.security import generate_password_hash

from models import db, Booking, Trek, DIFFICULTIES
from utils import current_user, role_required

user_bp = Blueprint("user", __name__, url_prefix="/user")


# ------------------------------------------------------------- trek browsing

def _filtered_open_treks():
    """Open treks filtered by search text, difficulty, and location."""
    q = request.args.get("q", "").strip()
    difficulty = request.args.get("difficulty", "")
    location = request.args.get("location", "")

    query = Trek.query.filter_by(status="Open")
    if q:
        query = query.filter(Trek.name.ilike(f"%{q}%"))
    if difficulty in DIFFICULTIES:
        query = query.filter_by(difficulty=difficulty)
    if location:
        query = query.filter_by(location=location)
    return query.order_by(Trek.start_date).all()


def _open_locations():
    """Distinct locations of open treks, for the filter dropdown."""
    rows = (
        db.session.query(Trek.location)
        .filter(Trek.status == "Open")
        .distinct()
        .order_by(Trek.location)
        .all()
    )
    return [r[0] for r in rows]


@user_bp.route("/dashboard")
@role_required("user")
def dashboard():
    me = current_user()
    treks = _filtered_open_treks()
    recent_bookings = (
        me.bookings.order_by(Booking.booking_date.desc()).limit(5).all()
    )
    return render_template(
        "user/dashboard.html",
        treks=treks, locations=_open_locations(),
        difficulties=DIFFICULTIES, recent_bookings=recent_bookings,
    )


@user_bp.route("/treks")
@role_required("user")
def treks():
    return render_template(
        "user/treks.html",
        treks=_filtered_open_treks(), locations=_open_locations(),
        difficulties=DIFFICULTIES,
    )


@user_bp.route("/treks/<int:trek_id>")
@role_required("user")
def trek_detail(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    already_booked = Booking.query.filter_by(
        user_id=current_user().id, trek_id=trek.id, status="Booked"
    ).first() is not None
    return render_template(
        "user/trek_detail.html", trek=trek, already_booked=already_booked
    )


# ------------------------------------------------------------------ booking

@user_bp.route("/treks/<int:trek_id>/book", methods=["POST"])
@role_required("user")
def book_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    me = current_user()

    already_booked = Booking.query.filter_by(
        user_id=me.id, trek_id=trek.id, status="Booked"
    ).first()

    # backend guards: open status, free slots, no duplicates
    if trek.status != "Open":
        flash("This trek is not open for booking.", "danger")
    elif trek.available_slots <= 0:
        flash("This trek is fully booked — no slots left.", "danger")
    elif already_booked:
        flash("You have already booked this trek.", "warning")
    else:
        db.session.add(Booking(user_id=me.id, trek_id=trek.id))
        db.session.commit()
        flash(f"Booking confirmed for '{trek.name}'!", "success")
        return redirect(url_for("user.bookings"))
    return redirect(url_for("user.trek_detail", trek_id=trek.id))


@user_bp.route("/bookings")
@role_required("user")
def bookings():
    mine = (
        current_user().bookings.order_by(Booking.booking_date.desc()).all()
    )
    return render_template("user/bookings.html", bookings=mine)


@user_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@role_required("user")
def cancel_booking(booking_id):
    booking = Booking.query.filter_by(
        id=booking_id, user_id=current_user().id
    ).first_or_404()

    if booking.status != "Booked":
        flash("Only active bookings can be cancelled.", "danger")
    elif booking.trek.status in ("Started", "Completed"):
        flash("This trek has already started — the booking cannot be cancelled.", "danger")
    else:
        booking.status = "Cancelled"
        db.session.commit()
        flash(f"Booking for '{booking.trek.name}' cancelled.", "info")
    return redirect(url_for("user.bookings"))


# ------------------------------------------------------------------ profile

@user_bp.route("/profile", methods=["GET", "POST"])
@role_required("user")
def profile():
    user = current_user()
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
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
            if password:
                user.password_hash = generate_password_hash(password)
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("user.profile"))
    return render_template("user/profile.html")
