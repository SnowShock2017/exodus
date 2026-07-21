"""
routes/crossfit.py
-------------------
Browse/filter the CrossFit template library, generate a new WOD on
demand, scale an existing one to a different difficulty, log a score, and
manage favorites.
"""

from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from extensions import db
from models import CrossfitWorkout, CrossfitLog, FavoriteCrossfit, Exercise
from logic.helpers import profile_to_dict, crossfit_to_dict, exercise_to_dict
from logic.crossfit_engine import filter_workouts, scale_workout, generate_workout, TYPES, DIFFICULTIES

bp = Blueprint("crossfit", __name__, url_prefix="/crossfit")


def _all_workouts():
    return [crossfit_to_dict(w) for w in CrossfitWorkout.query.all()]


@bp.route("/")
@login_required
def index():
    profile = current_user.profile
    wtype = request.args.get("type")
    difficulty = request.args.get("difficulty")
    equipment_only = request.args.get("equipment_only") == "1"

    workouts = _all_workouts()
    equipment = profile.equipment if equipment_only else None
    filtered = filter_workouts(workouts, wtype=wtype, difficulty=difficulty, equipment=equipment)

    favorite_keys = {f.workout_key for f in FavoriteCrossfit.query.filter_by(user_id=current_user.id).all()}

    return render_template("crossfit/index.html", profile=profile, workouts=filtered,
                            types=TYPES, difficulties=DIFFICULTIES, active_type=wtype,
                            active_difficulty=difficulty, equipment_only=equipment_only,
                            favorite_keys=favorite_keys)


@bp.route("/generate", methods=["POST"])
@login_required
def generate():
    profile = current_user.profile
    profile_dict = profile_to_dict(profile)
    exercises = [exercise_to_dict(e) for e in Exercise.query.all()]
    wtype = request.form.get("type", "AMRAP")
    duration = request.form.get("duration_min", type=int, default=15)
    wod = generate_workout(exercises, profile_dict, wtype=wtype, duration_min=duration)
    return render_template("crossfit/detail.html", profile=profile, w=wod, generated=True,
                            movement_exercises={m["exercise_key"]: Exercise.query.filter_by(key=m["exercise_key"]).first()
                                                 for m in wod["movements"]})


@bp.route("/<key>")
@login_required
def detail(key):
    profile = current_user.profile
    w = CrossfitWorkout.query.filter_by(key=key).first_or_404()
    w_dict = crossfit_to_dict(w)
    target_difficulty = request.args.get("difficulty", w.difficulty)
    movements = scale_workout(w_dict, target_difficulty) if target_difficulty != w.difficulty else w.movements
    movement_exercises = {m["exercise_key"]: Exercise.query.filter_by(key=m["exercise_key"]).first()
                           for m in movements}
    is_favorite = FavoriteCrossfit.query.filter_by(user_id=current_user.id, workout_key=key).first() is not None
    return render_template("crossfit/detail.html", profile=profile, w=w_dict, movements=movements,
                            movement_exercises=movement_exercises, target_difficulty=target_difficulty,
                            difficulties=DIFFICULTIES, is_favorite=is_favorite, generated=False)


@bp.route("/<key>/log", methods=["POST"])
@login_required
def log_score(key):
    db.session.add(CrossfitLog(
        user_id=current_user.id, date=date.today().isoformat(), workout_key=key,
        score_text=request.form.get("score", ""), difficulty_used=request.form.get("difficulty", ""),
        notes=request.form.get("notes", ""),
    ))
    db.session.commit()
    flash("Score logged." if current_user.profile.language != "ro" else "Scor înregistrat.", "success")
    return redirect(url_for("crossfit.detail", key=key))


@bp.route("/<key>/favorite", methods=["POST"])
@login_required
def toggle_favorite(key):
    existing = FavoriteCrossfit.query.filter_by(user_id=current_user.id, workout_key=key).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(FavoriteCrossfit(user_id=current_user.id, workout_key=key))
    db.session.commit()
    return redirect(request.referrer or url_for("crossfit.index"))
