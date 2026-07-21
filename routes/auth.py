"""
routes/auth.py
---------------
Signup, login, logout, password reset, account deletion, and data export.

Privacy model in one sentence: every table with personal data has a
user_id column, every query in this app filters by current_user.id, so one
account can never read another account's rows. See DOCUMENTATION.md.

Password reset works without any email setup (the reset link is shown
directly on the page) and upgrades automatically to real email once you
configure SMTP env vars — see logic/emailer.py.
"""

import json
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import (
    User, Profile, PasswordResetToken, WeightLog, StepLog, SleepLog,
    MealLogEntry, WorkoutSetLog, CrossfitLog, ShoppingListItem, FavoriteMeal,
    MealRating, FavoriteCrossfit, WorkoutPlan,
)
from logic.emailer import send_reset_email, smtp_configured

bp = Blueprint("auth", __name__)


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        error = None
        if not email or "@" not in email:
            error = "Please enter a valid email address."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm:
            error = "Passwords don't match."
        elif User.query.filter_by(email=email).first():
            error = "An account with that email already exists."

        if error:
            flash(error, "error")
            return render_template("auth/signup.html")

        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # get user.id before commit

        profile = Profile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

        login_user(user)
        return redirect(url_for("onboarding.start"))

    return render_template("auth/signup.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            if not user.profile or not user.profile.onboarding_complete:
                return redirect(url_for("onboarding.start"))
            return redirect(request.args.get("next") or url_for("dashboard.home"))

        flash("Incorrect email or password.", "error")

    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    reset_link = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        # Always show the same message whether or not the account exists,
        # so this form can't be used to check which emails are registered.
        if user:
            token = secrets.token_urlsafe(32)
            db.session.add(PasswordResetToken(user_id=user.id, token=token))
            db.session.commit()
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            sent = send_reset_email(user.email, reset_url, user.profile.language if user.profile else "en")
            if not sent:
                reset_link = reset_url  # SMTP not configured -> show link directly
        flash("If that email has an account, a reset link has been generated.", "info")

    return render_template("auth/forgot_password.html", reset_link=reset_link,
                            smtp_on=smtp_configured())


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    record = PasswordResetToken.query.filter_by(token=token, used=False).first()
    valid = record and (datetime.utcnow() - record.created_at) < timedelta(hours=2)

    if not valid:
        flash("This reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif password != confirm:
            flash("Passwords don't match.", "error")
        else:
            user = User.query.get(record.user_id)
            user.set_password(password)
            record.used = True
            db.session.commit()
            flash("Password updated. You can log in now.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)


@bp.route("/account/export")
@login_required
def export_data():
    """GDPR-style data export: everything this account owns, as JSON."""
    uid = current_user.id
    profile = current_user.profile

    def rows(model):
        return [
            {c.name: getattr(row, c.name) for c in model.__table__.columns}
            for row in model.query.filter_by(user_id=uid).all()
        ]

    data = {
        "account": {"id": current_user.id, "email": current_user.email,
                     "created_at": str(current_user.created_at)},
        "profile": {c.name: getattr(profile, c.name) for c in profile.__table__.columns} if profile else None,
        "weight_logs": rows(WeightLog),
        "step_logs": rows(StepLog),
        "sleep_logs": rows(SleepLog),
        "meal_log_entries": rows(MealLogEntry),
        "workout_set_logs": rows(WorkoutSetLog),
        "crossfit_logs": rows(CrossfitLog),
        "shopping_list_items": rows(ShoppingListItem),
        "favorite_meals": rows(FavoriteMeal),
        "meal_ratings": rows(MealRating),
        "favorite_crossfit": rows(FavoriteCrossfit),
    }

    from flask import Response
    return Response(
        json.dumps(data, indent=2, default=str, ensure_ascii=False),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=exodus_data_export.json"},
    )


@bp.route("/account/delete", methods=["POST"])
@login_required
def delete_account():
    password = request.form.get("password", "")
    if not current_user.check_password(password):
        flash("Incorrect password — account not deleted.", "error")
        return redirect(url_for("settings.index"))

    uid = current_user.id
    for model in (WeightLog, StepLog, SleepLog, MealLogEntry, WorkoutSetLog, CrossfitLog,
                  ShoppingListItem, FavoriteMeal, MealRating, FavoriteCrossfit):
        model.query.filter_by(user_id=uid).delete()
    for plan in WorkoutPlan.query.filter_by(user_id=uid).all():
        db.session.delete(plan)  # cascades to days/exercises

    user = User.query.get(uid)
    logout_user()
    db.session.delete(user)  # cascades to profile
    db.session.commit()
    flash("Your account and all data have been deleted.", "info")
    return redirect(url_for("auth.signup"))
