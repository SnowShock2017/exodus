"""
routes/settings.py
-------------------
Profile editing (stats, equipment, diet/allergies/injuries, language,
units), goal switching (delegates to goal_engine so the gradual-transition
explanation shows up), and the account-management links (export/delete
live in routes/auth.py, this page just links to them).
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from extensions import db
from logic.goal_engine import switch_goal, GOAL_LABELS, GOAL_DESCRIPTIONS

bp = Blueprint("settings", __name__, url_prefix="/settings")


def _split_csv(value):
    return [v.strip() for v in value.split(",") if v.strip()] if value else []


@bp.route("/")
@login_required
def index():
    profile = current_user.profile
    return render_template("settings.html", profile=profile,
                            goal_labels=GOAL_LABELS, goal_descriptions=GOAL_DESCRIPTIONS)


@bp.route("/save", methods=["POST"])
@login_required
def save():
    profile = current_user.profile
    form = request.form

    profile.name = form.get("name", "").strip()
    profile.age = int(form.get("age") or profile.age)
    profile.sex = form.get("sex", profile.sex)
    profile.height_cm = float(form.get("height_cm") or profile.height_cm)
    profile.weight_kg = float(form.get("weight_kg") or profile.weight_kg)
    tw = form.get("target_weight_kg")
    profile.target_weight_kg = float(tw) if tw else None
    profile.experience_level = form.get("experience_level", profile.experience_level)
    profile.activity_level = form.get("activity_level", profile.activity_level)
    profile.training_days_per_week = int(form.get("training_days_per_week") or profile.training_days_per_week)
    profile.preferred_style = form.get("preferred_style", profile.preferred_style)
    profile.equipment = form.getlist("equipment")
    profile.dietary_prefs = form.getlist("dietary_prefs")
    profile.allergies = _split_csv(form.get("allergies", ""))
    profile.dislikes = _split_csv(form.get("dislikes", ""))
    profile.injuries = form.get("injuries", "").strip()
    profile.injury_tags = form.getlist("injury_tags")
    profile.language = form.get("language", profile.language)
    profile.units = form.get("units", profile.units)
    profile.meal_frequency = int(form.get("meal_frequency") or profile.meal_frequency)
    profile.sleep_hours = float(form.get("sleep_hours") or profile.sleep_hours)
    st = form.get("step_target")
    profile.step_target = int(st) if st else None
    profile.prs_kg = {
        "bench": float(form.get("pr_bench") or 0),
        "squat": float(form.get("pr_squat") or 0),
        "deadlift": float(form.get("pr_deadlift") or 0),
        "pullups_clean_reps": int(form.get("pr_pullups") or 0),
    }

    new_goal = form.get("goal")
    if new_goal and new_goal != profile.goal:
        explanation = switch_goal(profile, new_goal)
        flash(explanation["ro" if profile.language == "ro" else "en"], "info")

    db.session.commit()
    flash("Saved." if profile.language != "ro" else "Salvat.", "success")
    return redirect(url_for("settings.index"))
