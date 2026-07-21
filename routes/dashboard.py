"""
routes/dashboard.py
--------------------
The Home tab: today's calorie/macro targets vs. logged so far, today's
workout (from the user's active plan, if any), weekly workout consistency,
weight trend, recent PRs, and one "recommendation of the day" pulled from
the same rule-based assistant used on the AI Assistant page.
"""

from datetime import date, timedelta

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from models import WeightLog, WorkoutSetLog, MealLogEntry, WorkoutPlan, WorkoutDay
from logic.helpers import profile_to_dict, meal_log_to_dict
from logic.cache import get_exercises
from logic.goal_engine import calculate_targets
from logic.nutrition_engine import daily_totals, progress_pct
from logic.progress_engine import personal_records, consistency_series
from logic.workout_engine import get_phase

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def home():
    if not current_user.profile or not current_user.profile.onboarding_complete:
        return redirect(url_for("onboarding.start"))

    profile = current_user.profile
    profile_dict = profile_to_dict(profile)
    today_str = date.today().isoformat()

    targets = calculate_targets(profile)

    meal_entries = [meal_log_to_dict(e) for e in
                    MealLogEntry.query.filter_by(user_id=current_user.id, date=today_str).all()]
    totals = daily_totals(meal_entries)
    kcal_pct = progress_pct(totals["kcal"], targets["target_calories"])

    weight_logs = [{"date": w.date, "weight_kg": w.weight_kg} for w in
                   WeightLog.query.filter_by(user_id=current_user.id).order_by(WeightLog.date).all()]
    weight_trend = None
    if len(weight_logs) >= 2:
        weight_trend = round(weight_logs[-1]["weight_kg"] - weight_logs[-2]["weight_kg"], 1)

    plan = WorkoutPlan.query.filter_by(user_id=current_user.id, is_active=True).first()
    today_day = None
    if plan:
        weekday = date.today().weekday()
        today_day = WorkoutDay.query.filter_by(plan_id=plan.id, weekday_index=weekday).first()

    exercises_by_key = {e["key"]: e for e in get_exercises()}

    set_logs = [{"date": s.date, "exercise_key": s.exercise_key, "weight_kg": s.weight_kg,
                 "reps_done": s.reps_done, "is_warmup": s.is_warmup}
                for s in WorkoutSetLog.query.filter_by(user_id=current_user.id).all()]
    recent_prs = personal_records(set_logs, exercises_by_key, period_days=7)[:3]

    consistency = consistency_series(set_logs, profile.training_days_per_week, period_days=7)
    week_progress = consistency[-1] if consistency else {"sessions": 0, "planned": profile.training_days_per_week}

    phase, ramp_week = get_phase(profile_dict)

    return render_template(
        "dashboard.html",
        profile=profile, targets=targets, totals=totals, kcal_pct=kcal_pct,
        weight_trend=weight_trend, plan=plan, today_day=today_day,
        exercises_by_key=exercises_by_key, recent_prs=recent_prs,
        week_progress=week_progress, phase=phase, ramp_week=ramp_week,
    )
