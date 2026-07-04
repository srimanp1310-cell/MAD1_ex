"""User (Trekker) routes (fleshed out in the User milestone)."""

from flask import Blueprint, render_template

from utils import role_required

user_bp = Blueprint("user", __name__, url_prefix="/user")


@user_bp.route("/dashboard")
@role_required("user")
def dashboard():
    return render_template("user/dashboard.html")
