"""
routes/workouts.py
-------------------
Everything workout-related except CrossFit (separate blueprint):
today's workout + set logging, the weekly plan builder/editor, exercise
replacement, exercise instruction pages, and the pre-workout readiness
check-in.
"""

from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user

from extensions import db
from models import (
    WorkoutPlan, WorkoutDay, PlanExercise, WorkoutSetLog, ReadinessCheckin,
)
from logic.helpers import profile_to_dict, set_log_to_dict
from logic.cache import get_exercises, get_exercise_by_key
from logic.workout_engine import (
    build_plan, default_plan_weekdays, STYLE_CONFIG, suggest_replacements,
    replacement_explanation, estimate_1rm, detect_pr, get_phase, ramp_weight,
)
from logic.safety import suggest_readiness_action, check_red_flags

bp = Blueprint("workouts", __name__, url_prefix="/workouts")

WEEKDAY_NAMES_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAY_NAMES_RO = ["Luni", "Marți", "Miercuri", "Joi", "Vineri", "Sâmbătă", "Duminică"]


def _all_exercises():
    return get_exercises()


def _active_plan():
    return WorkoutPlan.query.filter_by(user_id=current_user.id, is_active=True).first()


@bp.route("/")
@login_required
def today():
    profile = current_user.profile
    profile_dict = profile_to_dict(profile)
    plan = _active_plan()
    weekday = date.today().weekday()
    day = WorkoutDay.query.filter_by(plan_id=plan.id, weekday_index=weekday).first() if plan else None
    phase, ramp_week = get_phase(profile_dict)

    day_exercises = []
    if day and not day.is_rest:
        # Bulk-fetch the most recent log per exercise in ONE query instead of
        # one query per exercise (previously N+1 — the main cause of this
        # page taking several seconds to load). Exercise rows themselves come
        # from the in-memory cache (logic/cache.py), so no query at all there.
        keys = [pe.exercise_key for pe in day.exercises]
        last_log_by_key = {}
        if keys:
            recent_logs = (WorkoutSetLog.query
                           .filter(WorkoutSetLog.user_id == current_user.id,
                                   WorkoutSetLog.exercise_key.in_(keys))
                           .order_by(WorkoutSetLog.date.desc()).all())
            for log in recent_logs:
                last_log_by_key.setdefault(log.exercise_key, log)

        for pe in day.exercises:
            ex_row = get_exercise_by_key(pe.exercise_key)
            weight = pe.target_weight_kg
            if phase == "ramp" and weight:
                weight = ramp_weight(weight, ramp_week)
            last_log = last_log_by_key.get(pe.exercise_key)
            day_exercises.append({"plan_exercise": pe, "exercise": ex_row, "ramped_weight": weight,
                                   "last_log": last_log})

    return render_template("workouts/today.html", profile=profile, plan=plan, day=day,
                            day_exercises=day_exercises, phase=phase, ramp_week=ramp_week)


@bp.route("/log", methods=["POST"])
@login_required
def log_set():
    form = request.form
    exercise_key = form.get("exercise_key")
    plan_exercise_id = form.get("plan_exercise_id", type=int)
    weight_kg = form.get("weight_kg", type=float)
    reps_done = form.get("reps_done", type=int)
    rpe = form.get("rpe", type=float)
    notes = form.get("notes", "")
    pain = form.get("pain") == "yes"
    set_number = form.get("set_number", type=int, default=1)
    today_str = date.today().isoformat()

    if check_red_flags(notes):
        flash(("This sounds serious — please see a doctor. Set not logged as a PR concern; "
                "talk to a professional." if current_user.profile.language != "ro" else
                "Asta sună serios — te rog vezi un medic."), "error")
        return redirect(url_for("workouts.today"))

    existing_logs = [set_log_to_dict(s) for s in
                     WorkoutSetLog.query.filter_by(user_id=current_user.id, exercise_key=exercise_key).all()]
    new_set = {"exercise_key": exercise_key, "date": today_str, "weight_kg": weight_kg, "reps_done": reps_done}
    is_pr = detect_pr(existing_logs, new_set)

    log = WorkoutSetLog(
        user_id=current_user.id, date=today_str, exercise_key=exercise_key,
        plan_exercise_id=plan_exercise_id, set_number=set_number, weight_kg=weight_kg,
        reps_done=reps_done, rpe=rpe, notes=notes, pain=pain, completed="completed",
    )
    db.session.add(log)
    db.session.commit()

    if is_pr and weight_kg and reps_done:
        e1rm = estimate_1rm(weight_kg, reps_done)
        msg = (f"New PR on {exercise_key.replace('_',' ')}! Est. 1RM ~{e1rm}kg." if current_user.profile.language != "ro"
               else f"Record personal nou la {exercise_key.replace('_',' ')}! 1RM estimat ~{e1rm}kg.")
        flash(msg, "pr")

    return redirect(url_for("workouts.today"))


# ---------------------------------------------------------------------------
# Plan builder / editor
# ---------------------------------------------------------------------------

@bp.route("/plan")
@login_required
def plan_view():
    plan = _active_plan()
    exercises = sorted(_all_exercises(), key=lambda e: (e["primary_muscle"], e["name_en"]))
    return render_template("workouts/plan.html", profile=current_user.profile, plan=plan,
                            styles=list(STYLE_CONFIG.keys()), exercises=exercises,
                            weekday_names_en=WEEKDAY_NAMES_EN, weekday_names_ro=WEEKDAY_NAMES_RO)


@bp.route("/plan/generate", methods=["POST"])
@login_required
def plan_generate():
    profile = current_user.profile
    form = request.form
    chosen_days = [int(d) for d in form.getlist("weekdays")]
    style = form.get("style", profile.preferred_style)
    equipment = form.getlist("equipment") or profile.equipment

    if not chosen_days:
        chosen_days = default_plan_weekdays(profile.training_days_per_week)

    profile_dict = profile_to_dict(profile)
    exercises = _all_exercises()
    days = build_plan(exercises, profile_dict, chosen_days, style, equipment=equipment)

    old_plan = _active_plan()
    if old_plan:
        old_plan.is_active = False

    new_plan = WorkoutPlan(user_id=current_user.id, name=f"Week of {date.today().isoformat()}",
                            style=style, week_start_date=date.today().isoformat(), is_active=True)
    db.session.add(new_plan)
    db.session.flush()

    for d in days:
        day_row = WorkoutDay(plan_id=new_plan.id, weekday_index=d["weekday_index"],
                              label=d.get("label_ro") if profile.language == "ro" else d.get("label_en", ""),
                              is_rest=d["is_rest"])
        db.session.add(day_row)
        db.session.flush()
        for ex in d["exercises"]:
            db.session.add(PlanExercise(
                day_id=day_row.id, exercise_key=ex["exercise_key"], order_index=ex["order_index"],
                sets=ex["sets"], reps=str(ex["reps"]), rest_seconds=ex["rest_seconds"],
                warmup_sets=ex["warmup_sets"], is_main_lift=ex["is_main_lift"],
            ))

    db.session.commit()
    flash("New weekly plan generated." if profile.language != "ro" else "Plan săptămânal nou generat.", "success")
    return redirect(url_for("workouts.plan_view"))


@bp.route("/plan/exercise/<int:pe_id>/update", methods=["POST"])
@login_required
def plan_exercise_update(pe_id):
    pe = PlanExercise.query.get(pe_id)
    if not pe or pe.day.plan.user_id != current_user.id:
        return redirect(url_for("workouts.plan_view"))
    form = request.form
    pe.sets = form.get("sets", type=int, default=pe.sets)
    pe.reps = form.get("reps", pe.reps)
    weight = form.get("target_weight_kg", type=float)
    pe.target_weight_kg = weight
    pe.rest_seconds = form.get("rest_seconds", type=int, default=pe.rest_seconds)
    pe.tempo = form.get("tempo", pe.tempo)
    pe.warmup_sets = form.get("warmup_sets", type=int, default=pe.warmup_sets)
    pe.notes = form.get("notes", pe.notes)
    db.session.commit()
    return redirect(url_for("workouts.plan_view"))


@bp.route("/plan/exercise/<int:pe_id>/delete", methods=["POST"])
@login_required
def plan_exercise_delete(pe_id):
    pe = PlanExercise.query.get(pe_id)
    if pe and pe.day.plan.user_id == current_user.id:
        db.session.delete(pe)
        db.session.commit()
    return redirect(url_for("workouts.plan_view"))


@bp.route("/plan/day/<int:day_id>/add-exercise", methods=["POST"])
@login_required
def plan_day_add_exercise(day_id):
    day = WorkoutDay.query.get(day_id)
    if not day or day.plan.user_id != current_user.id:
        return redirect(url_for("workouts.plan_view"))
    exercise_key = request.form.get("exercise_key")
    ex_row = get_exercise_by_key(exercise_key)
    if ex_row:
        existing_count = len(day.exercises)
        same_muscle_count = sum(
            1 for pe in day.exercises
            if (get_exercise_by_key(pe.exercise_key) or {}).get("primary_muscle") == ex_row["primary_muscle"]
        )
        if existing_count >= 6:
            flash(("This day already has 6+ exercises — that's a lot of volume for one session." if
                   current_user.profile.language != "ro" else
                   "Ziua are deja 6+ exerciții — e mult volum pentru o sesiune."), "warning")
        if same_muscle_count >= 2:
            flash((f"You already have {same_muscle_count} exercises for {ex_row['primary_muscle']} today — "
                   f"consider whether this adds unnecessary repetition." if current_user.profile.language != "ro" else
                   f"Ai deja {same_muscle_count} exerciții pentru {ex_row['primary_muscle']} azi — "
                   f"ia în calcul dacă asta adaugă repetiție inutilă."), "warning")
        db.session.add(PlanExercise(
            day_id=day.id, exercise_key=exercise_key, order_index=len(day.exercises),
            sets=3, reps="8-12", rest_seconds=90,
        ))
        db.session.commit()
    return redirect(url_for("workouts.plan_view"))


@bp.route("/plan/day/<int:day_id>/toggle-rest", methods=["POST"])
@login_required
def plan_day_toggle_rest(day_id):
    """Flip a single day between training/rest without touching any other
    day or deleting its exercises — lets you reschedule your week (e.g.
    turn Friday into a rest day, or turn Sunday into a training day) without
    regenerating the whole plan, which would wipe any exercises you'd
    manually built into a custom day."""
    day = WorkoutDay.query.get(day_id)
    if not day or day.plan.user_id != current_user.id:
        return redirect(url_for("workouts.plan_view"))
    day.is_rest = not day.is_rest
    if not day.label or day.label in ("Rest", "Odihnă"):
        n = WorkoutDay.query.filter(WorkoutDay.plan_id == day.plan_id,
                                     WorkoutDay.weekday_index <= day.weekday_index,
                                     WorkoutDay.is_rest == False).count()
        day.label = f"Custom Day {max(n, 1)}" if current_user.profile.language != "ro" else f"Zi Personalizată {max(n, 1)}"
    db.session.commit()
    return redirect(url_for("workouts.plan_view"))


@bp.route("/plan/day/<int:day_id>/move", methods=["POST"])
@login_required
def plan_day_move(day_id):
    """Move a day to a different weekday. If another day in the plan
    already occupies that weekday, the two days simply swap places (and
    swap their exercises with them) — this is how you reschedule your
    week (e.g. move Tuesday's session to Thursday) without losing anything
    you've built."""
    day = WorkoutDay.query.get(day_id)
    if not day or day.plan.user_id != current_user.id:
        return redirect(url_for("workouts.plan_view"))
    new_weekday = request.form.get("weekday_index", type=int)
    if new_weekday is None or not (0 <= new_weekday <= 6) or new_weekday == day.weekday_index:
        return redirect(url_for("workouts.plan_view"))

    other_day = WorkoutDay.query.filter_by(plan_id=day.plan_id, weekday_index=new_weekday).first()
    if other_day:
        other_day.weekday_index, day.weekday_index = day.weekday_index, new_weekday
    else:
        day.weekday_index = new_weekday
    db.session.commit()
    return redirect(url_for("workouts.plan_view"))


# ---------------------------------------------------------------------------
# Exercise replacement
# ---------------------------------------------------------------------------

@bp.route("/replace/<int:pe_id>")
@login_required
def replace_view(pe_id):
    pe = PlanExercise.query.get_or_404(pe_id)
    if pe.day.plan.user_id != current_user.id:
        return redirect(url_for("workouts.plan_view"))
    profile_dict = profile_to_dict(current_user.profile)
    exercises = _all_exercises()
    suggestions = suggest_replacements(exercises, pe.exercise_key, profile_dict)
    explanations = {}
    lang = current_user.profile.language
    for r in suggestions["recommended"]:
        explanations[r["key"]] = replacement_explanation(suggestions["original"], r, lang)
    return render_template("workouts/replace.html", profile=current_user.profile, pe=pe,
                            suggestions=suggestions, explanations=explanations)


@bp.route("/replace/<int:pe_id>", methods=["POST"])
@login_required
def replace_apply(pe_id):
    pe = PlanExercise.query.get_or_404(pe_id)
    if pe.day.plan.user_id != current_user.id:
        return redirect(url_for("workouts.plan_view"))
    new_key = request.form.get("new_exercise_key")
    if new_key:
        pe.exercise_key = new_key
        pe.target_weight_kg = None
        db.session.commit()
        flash("Exercise replaced." if current_user.profile.language != "ro" else "Exercițiu înlocuit.", "success")
    return redirect(url_for("workouts.plan_view"))


# ---------------------------------------------------------------------------
# Exercise instructions
# ---------------------------------------------------------------------------

@bp.route("/exercise/<key>")
@login_required
def exercise_detail(key):
    ex = get_exercise_by_key(key)
    if not ex:
        abort(404)
    easier = get_exercise_by_key(ex.get("easier_variation")) if ex.get("easier_variation") else None
    harder = get_exercise_by_key(ex.get("harder_variation")) if ex.get("harder_variation") else None
    return render_template("workouts/exercise_detail.html", profile=current_user.profile,
                            ex=ex, easier=easier, harder=harder)


@bp.route("/exercises")
@login_required
def exercise_library():
    muscle = request.args.get("muscle")
    all_exercises = get_exercises()
    exercises = [e for e in all_exercises if not muscle or e["primary_muscle"] == muscle]
    exercises.sort(key=lambda e: (e["primary_muscle"], e["name_en"]))
    muscles = sorted({e["primary_muscle"] for e in all_exercises})
    return render_template("workouts/library.html", profile=current_user.profile,
                            exercises=exercises, muscles=muscles, active_muscle=muscle)


# ---------------------------------------------------------------------------
# Readiness check-in
# ---------------------------------------------------------------------------

@bp.route("/readiness", methods=["GET", "POST"])
@login_required
def readiness():
    result = None
    if request.method == "POST":
        form = request.form
        result = suggest_readiness_action(
            energy=form.get("energy", type=int, default=3),
            sleep_quality=form.get("sleep_quality", type=int, default=3),
            soreness=form.get("soreness", type=int, default=3),
            stress=form.get("stress", type=int, default=3),
            available_minutes=form.get("available_minutes", type=int),
            planned_minutes=60,
            pain_notes=form.get("pain_notes", ""),
        )
        db.session.add(ReadinessCheckin(
            user_id=current_user.id, date=date.today().isoformat(),
            energy=form.get("energy", type=int), sleep_quality=form.get("sleep_quality", type=int),
            soreness=form.get("soreness", type=int), stress=form.get("stress", type=int),
            available_minutes=form.get("available_minutes", type=int),
            pain_notes=form.get("pain_notes", ""), suggested_action=result["action"],
        ))
        db.session.commit()

    return render_template("workouts/readiness.html", profile=current_user.profile, result=result)
