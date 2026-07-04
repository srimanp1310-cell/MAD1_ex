"""Database models for the Trekking Management Application.

Tables: User, StaffProfile, Trek, Booking.
Relationships:
    Trek Staff (User) <-> Trek        one staff can be assigned many treks
    Trek           <-> Booking        one trek has many bookings
    User           <-> Booking        one user has many bookings
    User           <-> StaffProfile   one-to-one (staff members only)
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ---------------------------------------------------------------------------
# Allowed values (kept as plain tuples so they can be reused in validation)
# ---------------------------------------------------------------------------
ROLES = ("admin", "staff", "user")
DIFFICULTIES = ("Easy", "Moderate", "Hard")
TREK_STATUSES = ("Pending", "Approved", "Open", "Closed", "Started", "Completed")
BOOKING_STATUSES = ("Booked", "Cancelled", "Completed")
STAFF_APPROVAL_STATUSES = ("Pending", "Approved", "Rejected")


class User(db.Model):
    """All accounts: admin (pre-seeded), trek staff, and trekkers."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")  # admin/staff/user
    is_blacklisted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # one-to-one: only staff accounts have a profile
    staff_profile = db.relationship(
        "StaffProfile", back_populates="user", uselist=False,
        cascade="all, delete-orphan",
    )
    # bookings made by this user (trekkers)
    bookings = db.relationship("Booking", back_populates="user", lazy="dynamic")
    # treks this user manages (staff)
    assigned_treks = db.relationship("Trek", back_populates="assigned_staff", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.id} {self.email} ({self.role})>"


class StaffProfile(db.Model):
    """Extra details for trek staff; approval is granted by the admin."""

    __tablename__ = "staff_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    contact_number = db.Column(db.String(20))
    approval_status = db.Column(
        db.String(10), nullable=False, default="Pending"
    )  # Pending / Approved / Rejected
    applied_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="staff_profile")

    def __repr__(self):
        return f"<StaffProfile user={self.user_id} {self.approval_status}>"


class Trek(db.Model):
    """A trekking event created and managed by the admin."""

    __tablename__ = "treks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    difficulty = db.Column(db.String(10), nullable=False)  # Easy/Moderate/Hard
    duration_days = db.Column(db.Integer, nullable=False)
    total_slots = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.String(12), nullable=False, default="Pending"
    )  # Pending / Approved / Open / Closed / Started / Completed
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    description = db.Column(db.Text)
    staff_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # assigned staff
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    assigned_staff = db.relationship("User", back_populates="assigned_treks")
    bookings = db.relationship("Booking", back_populates="trek", lazy="dynamic")

    @property
    def booked_count(self):
        """Number of active (non-cancelled) bookings."""
        return self.bookings.filter(Booking.status != "Cancelled").count()

    @property
    def available_slots(self):
        """Slots remaining — always total capacity minus active bookings."""
        return max(self.total_slots - self.booked_count, 0)

    def __repr__(self):
        return f"<Trek {self.id} {self.name} [{self.status}]>"


class Booking(db.Model):
    """A record of a user booking a trek."""

    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey("treks.id"), nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(
        db.String(10), nullable=False, default="Booked"
    )  # Booked / Cancelled / Completed
    payment_status = db.Column(db.String(10), nullable=False, default="Paid")

    user = db.relationship("User", back_populates="bookings")
    trek = db.relationship("Trek", back_populates="bookings")

    def __repr__(self):
        return f"<Booking {self.id} user={self.user_id} trek={self.trek_id} {self.status}>"
