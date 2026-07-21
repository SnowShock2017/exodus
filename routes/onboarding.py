"""
routes/onboarding.py
---------------------
A 4-step onboarding wizard that fills in every field listed in the app
spec (stats, goal, experience, equipment, diet, allergies, injuries,
language, units, meal frequency, sleep, step target). Each step saves to
the DB immediately (so nothing is lost if the user closes the tab),
and the final step marks the profile complete and redirects to the
dashboard, which then runs the goal engine for the first time.
"""

from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user

from extensions import db

bp = Blueprint("onboarding", __name__, url_prefix="/onboarding")

STEPS = [1, 2, 3, 4]


def _split_csv(value):
    return [v.strip() for v in value.split(",") if v.strip()] if value else []


@bp.route("/")
@login_required
def start():
    return redirect(url_for("onboarding.step", n=1))


@bp.route("/step/<int:n>", methods=["GET", "POST"])
@login_required
def step(n):
    if n not in STEPS:
        return redirect(url_for("onboarding.step", n=1))

    profile = current_user.profile

    if request.method == "POST":
        form = request.form

        if n == 1:
            profile.name = form.get("name", "").strip()
            profile.age = int(form.get("age") or 25)
            profile.sex = form.get("sex", "male")
            profile.height_cm = float(form.get("height_cm") or 175)
            profile.weight_kg = float(form.get("weight_kg") or 75)
            tw = form.get("target_weight_kg")
            profile.target_weight_kg = float(tw) if tw else None
            profile.language = form.get("language", "en")
            profile.units = form.get("units", "kg")

        elif n == 2:
            profile.goal = form.get("goal", "lean_maintain_strength")
            profile.experience_level = form.get("experience_level", "beginner")
            profile.activity_level = form.get("activity_level", "moderate")
            profile.training_days_per_week = int(form.get("training_days_per_week") or 4)
            profile.preferred_style = form.get("preferred_style", "upper_lower")
            profile.equipment = form.getlist("equipment")

        elif n == 3:
            profile.dietary_prefs = form.getlist("dietary_prefs")
            profile.allergies = _split_csv(form.get("allergies", ""))
            profile.dislikes = _split_csv(form.get("dislikes", ""))
            profile.meal_frequency = int(form.get("meal_frequency") or 4)

        elif n == 4:
            profile.injuries = form.get("injuries", "").strip()
            profile.injury_tags = form.getlist("injury_tags")
            profile.sleep_hours = float(form.get("sleep_hours") or 7.5)
            st = form.get("step_target")
            profile.step_target = int(st) if st else None
            prs = {
                "bench": float(form.get("pr_bench") or 0),
                "squat": float(form.get("pr_squat") or 0),
                "deadlift": float(form.get("pr_deadlift") or 0),
                "pullups_clean_reps": int(form.get("pr_pullups") or 0),
            }
            profile.prs_kg = prs
            profile.onboarding_complete = True

        db.session.commit()

        if n < 4:
            return redirect(url_for("onboarding.step", n=n + 1))
        return redirect(url_for("dashboard.home"))

    return render_template(f"onboarding/step{n}.html", profile=profile, step=n, total=len(STEPS))
