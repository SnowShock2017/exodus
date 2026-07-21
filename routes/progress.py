"""
routes/progress.py
-------------------
Charts + weekly summary. Supports filtering by period (week/month/3mo/6mo/
year/custom) and by exercise for the strength chart.
"""

from datetime import date

from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from models import WeightLog, WorkoutSetLog, MealLogEntry, StepLog
from logic.helpers import profile_to_dict
from logic.cache import get_exercises
from logic.goal_engine import calculate_targets
from logic.progress_engine import (
    weight_series, e1rm_series, volume_series, consistency_series,
    calorie_and_protein_series, step_series, personal_records, weekly_summary,
)

bp = Blueprint("progress", __name__, url_prefix="/progress")

PERIOD_DAYS = {"week": 7, "month": 30, "3months": 90, "6months": 180, "year": 365}


@bp.route("/")
@login_required
def index():
    profile = current_user.profile
    period = request.args.get("period", "month")
    days = PERIOD_DAYS.get(period, 30)

    weight_logs = [{"date": w.date, "weight_kg": w.weight_kg} for w in
                   WeightLog.query.filter_by(user_id=current_user.id).all()]
    set_logs = [{"date": s.date, "exercise_key": s.exercise_key, "weight_kg": s.weight_kg,
                "reps_done": s.reps_done, "is_warmup": s.is_warmup} for s in
                WorkoutSetLog.query.filter_by(user_id=current_user.id).all()]
    meal_entries = [{"date": e.date, "kcal": e.kcal, "protein_g": e.protein_g} for e in
                    MealLogEntry.query.filter_by(user_id=current_user.id).all()]
    step_logs = [{"date": s.date, "steps": s.steps} for s in
                StepLog.query.filter_by(user_id=current_user.id).all()]

    exercises_by_key = {e["key"]: e for e in get_exercises()}
    exercise_key = request.args.get("exercise", "bench_press")

    targets = calculate_targets(profile)

    w_series = weight_series(weight_logs, days)
    e1_series = e1rm_series(set_logs, exercise_key, days)
    vol_series = volume_series(set_logs, days)
    cons_series = consistency_series(set_logs, profile.training_days_per_week, days)
    cal_series, protein_hit_days = calorie_and_protein_series(meal_entries, targets["protein_g"], days)
    steps_series = step_series(step_logs, days)
    prs = personal_records(set_logs, exercises_by_key)
    summary = weekly_summary(weight_logs, set_logs, meal_entries, profile_to_dict(profile),
                              targets, exercises_by_key, lang=profile.language)

    return render_template(
        "progress.html", profile=profile, period=period, exercise_key=exercise_key,
        exercises=list(exercises_by_key.values()), weight_series=w_series, e1rm_series=e1_series,
        volume_series=vol_series, consistency_series=cons_series, calorie_series=cal_series,
        steps_series=steps_series, prs=prs, summary=summary, protein_hit_days=protein_hit_days,
    )
