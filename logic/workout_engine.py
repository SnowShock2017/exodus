"""
workout_engine.py
------------------
Generates Absalon's 4-day Upper/Lower workout plan and applies simple,
transparent progressive-overload rules on top of it.

Weekly schedule (fixed, 4 training days matching "I work out 4x/week"):
    Monday    -> Upper A (bench-focused, strength)
    Tuesday   -> Lower A (squat-focused, strength)
    Wednesday -> Rest
    Thursday  -> Upper B (pull-up / back focused, hypertrophy)
    Friday    -> Lower B (deadlift-focused, strength)
    Saturday  -> Rest
    Sunday    -> Rest

Why a ramp phase exists
------------------------
The user was untrained for ~4 weeks and gained fat/lost some conditioning.
Jumping straight back to old PR-based working weights is a common way to
get hurt (tendons/CNS detrain faster than muscle memory suggests). So for
the first 3 weeks after `return_to_training_start_date` we prescribe a
percentage ramp (70% -> 80% -> 85% of last known PR) before handing off to
normal double-progression.

Double progression (normal phase)
----------------------------------
For each main barbell lift: if the last logged session hit the prescribed
reps on every set at RPE <= 8 (or RPE not logged), the next session's
target weight goes up by a small fixed increment. Otherwise it repeats.
This is the same simple rule used in most beginner/intermediate strength
programs (StrongLifts, GreyStress, etc.) -- easy to reason about, no
guessing required.
"""

from datetime import date, datetime

WEEKDAY_TO_SPLIT = {
    0: "upper_a",   # Monday
    1: "lower_a",   # Tuesday
    2: "rest",      # Wednesday
    3: "upper_b",   # Thursday
    4: "lower_b",   # Friday
    5: "rest",      # Saturday
    6: "rest",      # Sunday
}

MAIN_LIFT_INCREMENT_KG = {
    "bench": 2.5,
    "squat": 5.0,
    "deadlift": 5.0,
}

# generic accessory work -- same pool every week, sets/reps are by feel
# (RPE 7-8), no weight prescription needed since it's not the focus lift.
ACCESSORIES = {
    "upper_a": [
        {"exercise": "Incline dumbbell press", "sets": 3, "reps": "8-10"},
        {"exercise": "Chest-supported row", "sets": 3, "reps": "8-10"},
        {"exercise": "Lateral raise", "sets": 3, "reps": "12-15"},
        {"exercise": "Triceps pushdown", "sets": 3, "reps": "10-12"},
    ],
    "upper_b": [
        {"exercise": "Overhead press", "sets": 3, "reps": "6-8"},
        {"exercise": "Barbell/DB row", "sets": 3, "reps": "8-10"},
        {"exercise": "Face pull", "sets": 3, "reps": "12-15"},
        {"exercise": "Biceps curl", "sets": 3, "reps": "10-12"},
    ],
    "lower_a": [
        {"exercise": "Romanian deadlift", "sets": 3, "reps": "8-10"},
        {"exercise": "Leg press", "sets": 3, "reps": "10-12"},
        {"exercise": "Calf raise", "sets": 4, "reps": "12-15"},
        {"exercise": "Hanging leg raise", "sets": 3, "reps": "10-15"},
    ],
    "lower_b": [
        {"exercise": "Front squat or leg press", "sets": 3, "reps": "8-10"},
        {"exercise": "Leg curl", "sets": 3, "reps": "10-12"},
        {"exercise": "Standing calf raise", "sets": 4, "reps": "12-15"},
        {"exercise": "Plank", "sets": 3, "reps": "45-60s"},
    ],
}

SPLIT_LABEL_KEY = {
    "upper_a": "Upper A (Bench focus)",
    "upper_b": "Upper B (Back / Pull-up focus)",
    "lower_a": "Lower A (Squat focus)",
    "lower_b": "Lower B (Deadlift focus)",
    "rest": "Rest",
}


def get_phase(profile, today=None):
    """Returns ('ramp', week_number) for the first 3 weeks back, else ('normal', None)."""
    today = today or date.today()
    start_str = profile.get("return_to_training_start_date")
    if not start_str:
        return "normal", None
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    days_in = (today - start).days
    if days_in < 0:
        days_in = 0
    week_number = (days_in // 7) + 1
    if week_number <= 3:
        return "ramp", week_number
    return "normal", None


def _last_session_for(workout_log, exercise_key):
    """Most recent logged entries for a given exercise key, most recent date first sets."""
    matches = [e for e in workout_log if e.get("exercise_key") == exercise_key]
    if not matches:
        return None
    matches.sort(key=lambda e: e.get("date", ""))
    last_date = matches[-1]["date"]
    return [e for e in matches if e["date"] == last_date]


def _next_main_lift_weight(profile, workout_log, lift_key, target_reps):
    """Double progression: bump weight if last session was clean, else repeat."""
    pr = profile.get("prs_kg", {}).get(lift_key, 0)
    last_sets = _last_session_for(workout_log, lift_key)
    if not last_sets:
        # no history yet -> start conservatively under the old PR
        return round(pr * 0.85, 1)

    last_weight = last_sets[-1].get("weight_kg", pr * 0.85)
    all_hit = all(
        (s.get("reps_done") or 0) >= target_reps and (s.get("rpe") is None or s.get("rpe") <= 8)
        for s in last_sets
    )
    if all_hit:
        return round(last_weight + MAIN_LIFT_INCREMENT_KG.get(lift_key, 2.5), 1)
    return round(last_weight, 1)


def _next_pullup_target(profile, workout_log):
    """Pull-ups are bodyweight -- progress by reps, then note to add weight once strong."""
    pr = profile.get("prs_kg", {}).get("pullups_clean_reps", 8)
    last_sets = _last_session_for(workout_log, "pullups")
    if not last_sets:
        return max(3, round(pr * 0.7)), "bodyweight"
    last_reps = last_sets[-1].get("reps_done", max(3, round(pr * 0.7)))
    all_hit = all((s.get("reps_done") or 0) >= last_reps for s in last_sets)
    note = "bodyweight"
    if all_hit and last_reps >= pr:
        note = "bodyweight (consider adding a small weight belt +2.5kg next block)"
        return last_reps, note
    if all_hit:
        return last_reps + 1, note
    return last_reps, note


def _ramp_main_lift(profile, lift_key, week_number):
    pr = profile.get("prs_kg", {}).get(lift_key, 0)
    pct_by_week = {1: 0.70, 2: 0.80, 3: 0.85}
    pct = pct_by_week.get(week_number, 0.85)
    reps_by_week = {1: 8, 2: 6, 3: 5}
    return round(pr * pct, 1), reps_by_week.get(week_number, 5)


def _ramp_pullups(profile, week_number):
    pr = profile.get("prs_kg", {}).get("pullups_clean_reps", 8)
    pct_by_week = {1: 0.60, 2: 0.70, 3: 0.80}
    pct = pct_by_week.get(week_number, 0.8)
    return max(3, round(pr * pct))


def build_day_plan(profile, workout_log, split_key, phase, week_number):
    """Returns dict describing one training day's exercises, or None for rest."""
    if split_key == "rest":
        return None

    main_lift_by_split = {
        "upper_a": ("bench", "Barbell bench press"),
        "lower_a": ("squat", "Barbell back squat"),
        "upper_b": ("pullups", "Weighted / clean pull-ups"),
        "lower_b": ("deadlift", "Barbell deadlift"),
    }
    lift_key, lift_label = main_lift_by_split[split_key]

    if lift_key == "pullups":
        if phase == "ramp":
            reps = _ramp_pullups(profile, week_number)
            sets = 3 if week_number == 1 else 4
            main = {"exercise": lift_label, "sets": sets, "reps": f"{reps} (bodyweight)",
                    "weight_kg": None}
        else:
            reps, note = _next_pullup_target(profile, workout_log)
            main = {"exercise": lift_label, "sets": 4, "reps": f"{reps} ({note})",
                    "weight_kg": None}
    else:
        if phase == "ramp":
            weight, reps = _ramp_main_lift(profile, lift_key, week_number)
            sets = 3 if week_number in (1, 2) else 4
            main = {"exercise": lift_label, "sets": sets, "reps": reps, "weight_kg": weight}
        else:
            target_reps = 5
            weight = _next_main_lift_weight(profile, workout_log, lift_key, target_reps)
            main = {"exercise": lift_label, "sets": 4, "reps": target_reps, "weight_kg": weight}

    main["exercise_key"] = lift_key
    day_plan = {
        "split_key": split_key,
        "label": SPLIT_LABEL_KEY[split_key],
        "main_lift": main,
        "accessories": ACCESSORIES[split_key],
    }
    return day_plan


def get_today_plan(profile, workout_log, today=None):
    today = today or date.today()
    split_key = WEEKDAY_TO_SPLIT[today.weekday()]
    phase, week_number = get_phase(profile, today)
    plan = build_day_plan(profile, workout_log, split_key, phase, week_number)
    return plan, phase, week_number


def get_week_overview(profile, workout_log, today=None):
    """Mon-Sun list of {weekday_index, split_key, label} for the weekly schedule view."""
    phase, week_number = get_phase(profile, today or date.today())
    overview = []
    for idx in range(7):
        split_key = WEEKDAY_TO_SPLIT[idx]
        overview.append({
            "weekday_index": idx,
            "split_key": split_key,
            "label": SPLIT_LABEL_KEY[split_key],
        })
    return overview, phase, week_number
