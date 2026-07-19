"""
app.py
------
Flask entry point for Exodus. Ties together the profile store and the
three "engines" (workout / nutrition / supplement / coach) and serves
a small mobile-friendly web UI.

Run it with:
    python app.py
Then open the printed address in Safari on your iPhone (same WiFi as
your computer) and use "Share -> Add to Home Screen" to get an app icon.

Routes
------
GET  /                 -> dashboard: today's workout summary, today's
                          nutrition targets, coach tips
GET  /workout          -> full weekly split + today's prescribed sets
POST /workout/log      -> save logged sets for today
GET  /meals            -> calorie/macro targets, today's logged food + totals,
                          meal ideas + supplements
POST /meals/log        -> log one food item (looked up in data/food_db.json,
                          scaled by quantity) for today
POST /meals/delete/<id> -> remove a logged food item
GET  /progress         -> weight history table/chart + calorie history chart
POST /progress/log     -> save a new body-weight entry
GET  /settings         -> edit profile (stats, PRs, language, goal)
POST /settings/save    -> persist profile edits
POST /toggle-language  -> switch en/ro, redirect back
"""

from datetime import date

from flask import Flask, render_template, request, redirect, url_for, session

from logic import profile_store as store
from logic.i18n import t
from logic.workout_engine import get_today_plan, get_week_overview, get_phase
from logic.nutrition_engine import (
    calculate_targets, get_meal_ideas, MEAL_TYPES,
    find_food, build_log_entry, daily_totals, progress_pct, calorie_history,
)
from logic.supplement_engine import get_recommendations, DISCLAIMER_EN, DISCLAIMER_RO
from logic.coach_engine import analyze

app = Flask(__name__)
app.secret_key = "exodus-local-dev-secret"  # single-user local app; fine as-is


def current_lang():
    profile = store.get_profile()
    return profile.get("language", "en")


@app.context_processor
def inject_globals():
    lang = current_lang()
    return {"t": lambda key: t(key, lang), "lang": lang, "today": date.today().isoformat()}


@app.route("/")
def dashboard():
    profile = store.get_profile()
    workout_log = store.get_workout_log()
    weight_log = store.get_weight_log()
    lang = profile.get("language", "en")

    plan, phase, week = get_today_plan(profile, workout_log)
    targets = calculate_targets(profile)
    tips = analyze(profile, weight_log, workout_log, lang)

    meal_log = store.get_meal_log()
    totals, _ = daily_totals(meal_log)
    kcal_pct = progress_pct(totals["kcal"], targets["target_calories"])

    return render_template(
        "index.html",
        profile=profile,
        plan=plan,
        phase=phase,
        week=week,
        targets=targets,
        tips=tips,
        totals=totals,
        kcal_pct=kcal_pct,
    )


@app.route("/workout", methods=["GET"])
def workout():
    profile = store.get_profile()
    workout_log = store.get_workout_log()
    plan, phase, week = get_today_plan(profile, workout_log)
    overview, _, _ = get_week_overview(profile, workout_log)
    return render_template("workout.html", profile=profile, plan=plan, phase=phase,
                            week=week, overview=overview)


@app.route("/workout/log", methods=["POST"])
def log_workout():
    form = request.form
    exercise_key = form.get("exercise_key")
    exercise_name = form.get("exercise_name")
    weight_kg = form.get("weight_kg")
    sets_count = int(form.get("sets_count", 1))
    entries = []
    for i in range(1, sets_count + 1):
        reps = form.get(f"reps_{i}")
        rpe = form.get(f"rpe_{i}")
        entries.append({
            "date": date.today().isoformat(),
            "exercise_key": exercise_key,
            "exercise": exercise_name,
            "weight_kg": float(weight_kg) if weight_kg else None,
            "reps_done": int(reps) if reps else None,
            "rpe": float(rpe) if rpe else None,
        })
    store.add_workout_entries(entries)
    return redirect(url_for("workout"))


@app.route("/meals")
def meals():
    profile = store.get_profile()
    lang = profile.get("language", "en")
    targets = calculate_targets(profile)
    meal_ideas = get_meal_ideas(lang)
    supplements = get_recommendations(profile)
    disclaimer = DISCLAIMER_RO if lang == "ro" else DISCLAIMER_EN

    food_db = store.get_food_db()
    meal_log = store.get_meal_log()
    totals, todays_entries = daily_totals(meal_log)
    todays_entries.sort(key=lambda e: e.get("id", ""))

    progress = {
        "kcal": progress_pct(totals["kcal"], targets["target_calories"]),
        "protein_g": progress_pct(totals["protein_g"], targets["protein_g"]),
        "carb_g": progress_pct(totals["carb_g"], targets["carb_g"]),
        "fat_g": progress_pct(totals["fat_g"], targets["fat_g"]),
    }

    return render_template(
        "meals.html", profile=profile, targets=targets, meal_ideas=meal_ideas,
        supplements=supplements, disclaimer=disclaimer, food_db=food_db,
        meal_types=MEAL_TYPES, todays_entries=todays_entries, totals=totals,
        progress=progress,
    )


@app.route("/meals/log", methods=["POST"])
def log_meal():
    profile = store.get_profile()
    lang = profile.get("language", "en")
    food_name = request.form.get("food_name")
    qty = request.form.get("qty")
    meal_type = request.form.get("meal_type", "snack")

    food = find_food(food_name, lang)
    if food and qty:
        try:
            qty_val = float(qty)
        except ValueError:
            qty_val = None
        if qty_val and qty_val > 0:
            entry = build_log_entry(food, qty_val, meal_type, lang)
            store.add_meal_entry(entry)
    return redirect(url_for("meals"))


@app.route("/meals/delete/<entry_id>", methods=["POST"])
def delete_meal(entry_id):
    store.delete_meal_entry(entry_id)
    return redirect(url_for("meals"))


@app.route("/progress")
def progress():
    profile = store.get_profile()
    targets = calculate_targets(profile)
    weight_log = store.get_weight_log()
    workout_log = store.get_workout_log()
    meal_log = store.get_meal_log()
    kcal_history = calorie_history(meal_log, days=14)
    return render_template(
        "progress.html", weight_log=weight_log, workout_log=workout_log,
        kcal_history=kcal_history, target_calories=targets["target_calories"],
    )


@app.route("/progress/log", methods=["POST"])
def log_weight():
    weight_kg = request.form.get("weight_kg")
    if weight_kg:
        store.add_weight_entry(weight_kg)
    return redirect(url_for("progress"))


@app.route("/settings")
def settings():
    profile = store.get_profile()
    return render_template("settings.html", profile=profile)


@app.route("/settings/save", methods=["POST"])
def save_settings():
    form = request.form
    updates = {
        "height_cm": float(form.get("height_cm")),
        "weight_kg": float(form.get("weight_kg")),
        "age": int(form.get("age")),
        "goal": form.get("goal"),
        "activity_level": form.get("activity_level"),
        "training_days_per_week": int(form.get("training_days_per_week")),
        "language": form.get("language"),
        "prs_kg": {
            "bench": float(form.get("pr_bench")),
            "deadlift": float(form.get("pr_deadlift")),
            "squat": float(form.get("pr_squat")),
            "pullups_clean_reps": int(form.get("pr_pullups")),
        },
    }
    store.update_profile(**updates)
    return redirect(url_for("settings"))


@app.route("/toggle-language", methods=["POST"])
def toggle_language():
    profile = store.get_profile()
    new_lang = "ro" if profile.get("language", "en") == "en" else "en"
    store.update_profile(language=new_lang)
    return redirect(request.referrer or url_for("dashboard"))


if __name__ == "__main__":
    import os
    # host="0.0.0.0" so your iPhone can reach it over WiFi at your
    # computer's local IP (see DOCUMENTATION.md for how to find it).
    # PORT env var is read so this same file works unchanged if you later
    # deploy it to Render/PythonAnywhere/etc (they assign their own port).
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("EXODUS_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
