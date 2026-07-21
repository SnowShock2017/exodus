"""
workout_engine.py (v2 — multi-user)
------------------------------------
Everything about assembling and adapting workout plans, as plain functions
that take/return simple dicts and lists — no Flask or SQLAlchemy imports
here, so this whole module can be unit-tested with plain Python (see the
test block used during development) and reused from any route.

The actual Exercise rows come from the database (models.Exercise); route
handlers pass them in here as a list of dicts (see `_ex_to_dict` helper in
routes/workouts.py) so this module stays framework-free.

Contents
--------
- EXPERIENCE_RANK / equipment / injury filtering for exercise selection
- STYLE_CONFIG: day blueprints for every requested split style
- build_plan(): turns a style + chosen days into a concrete weekly plan
- suggest_replacements(): the "Replace Exercise" recommender
- estimate_1rm(), detect_pr(), volume_by_muscle(): logging analytics
- ramp phase (returning after a layoff) — generalized from single-user v1
"""

from datetime import date, datetime

EXPERIENCE_RANK = {"beginner": 1, "intermediate": 2, "advanced": 3}

EMPHASIS_SCHEMES = {
    "strength": {"main": (5, "3-5"), "accessory": (3, "8-10")},
    "hypertrophy": {"main": (4, "8-10"), "accessory": (3, "10-15")},
    "balanced": {"main": (4, "5-8"), "accessory": (3, "8-12")},
    "bodyweight": {"main": (4, "8-15"), "accessory": (3, "10-20")},
    "powerbuilding": {"main": (5, "3-5"), "accessory": (3, "10-15")},
}

STYLE_CONFIG = {
    "full_body": {"emphasis": "balanced", "days": [
        {"name_en": "Full Body A", "name_ro": "Corp Întreg A",
         "slots": [("quads", "main"), ("chest", "main"), ("lats", "main"), ("hamstrings", "accessory"), ("core", "accessory")]},
        {"name_en": "Full Body B", "name_ro": "Corp Întreg B",
         "slots": [("hamstrings", "main"), ("front_delts", "main"), ("lats", "main"), ("quads", "accessory"), ("core", "accessory")]},
        {"name_en": "Full Body C", "name_ro": "Corp Întreg C",
         "slots": [("chest", "main"), ("quads", "main"), ("lats", "main"), ("side_delts", "accessory"), ("core", "accessory")]},
    ]},
    "upper_lower": {"emphasis": "balanced", "days": [
        {"name_en": "Upper A", "name_ro": "Partea Superioară A",
         "slots": [("chest", "main"), ("lats", "accessory"), ("side_delts", "accessory"), ("triceps", "accessory")]},
        {"name_en": "Lower A", "name_ro": "Partea Inferioară A",
         "slots": [("quads", "main"), ("hamstrings", "accessory"), ("calves", "accessory"), ("core", "accessory")]},
        {"name_en": "Upper B", "name_ro": "Partea Superioară B",
         "slots": [("front_delts", "main"), ("lats", "main"), ("rear_delts", "accessory"), ("biceps", "accessory")]},
        {"name_en": "Lower B", "name_ro": "Partea Inferioară B",
         "slots": [("hamstrings", "main"), ("quads", "accessory"), ("calves", "accessory"), ("core", "accessory")]},
    ]},
    "push_pull_legs": {"emphasis": "hypertrophy", "days": [
        {"name_en": "Push", "name_ro": "Împins",
         "slots": [("chest", "main"), ("front_delts", "main"), ("side_delts", "accessory"), ("triceps", "accessory")]},
        {"name_en": "Pull", "name_ro": "Tras",
         "slots": [("lats", "main"), ("rear_delts", "accessory"), ("biceps", "accessory"), ("core", "accessory")]},
        {"name_en": "Legs", "name_ro": "Picioare",
         "slots": [("quads", "main"), ("hamstrings", "main"), ("calves", "accessory"), ("core", "accessory")]},
    ]},
    "bro_split": {"emphasis": "hypertrophy", "days": [
        {"name_en": "Chest", "name_ro": "Piept", "slots": [("chest", "main"), ("chest", "accessory"), ("triceps", "accessory")]},
        {"name_en": "Back", "name_ro": "Spate", "slots": [("lats", "main"), ("lats", "accessory"), ("rear_delts", "accessory")]},
        {"name_en": "Shoulders", "name_ro": "Umeri", "slots": [("front_delts", "main"), ("side_delts", "accessory"), ("rear_delts", "accessory")]},
        {"name_en": "Legs", "name_ro": "Picioare", "slots": [("quads", "main"), ("hamstrings", "main"), ("calves", "accessory")]},
        {"name_en": "Arms", "name_ro": "Brațe", "slots": [("biceps", "main"), ("triceps", "main"), ("core", "accessory")]},
    ]},
    "strength": {"emphasis": "strength", "days": [
        {"name_en": "Squat Day", "name_ro": "Ziua de Genuflexiuni", "slots": [("quads", "main"), ("core", "accessory")]},
        {"name_en": "Bench Day", "name_ro": "Ziua de Împins", "slots": [("chest", "main"), ("triceps", "accessory")]},
        {"name_en": "Deadlift Day", "name_ro": "Ziua de Îndreptări", "slots": [("hamstrings", "main"), ("lats", "accessory")]},
        {"name_en": "Overhead Press Day", "name_ro": "Ziua de Împins Deasupra Capului", "slots": [("front_delts", "main"), ("lats", "accessory")]},
    ]},
    "hypertrophy": {"emphasis": "hypertrophy", "days": [
        {"name_en": "Push", "name_ro": "Împins", "slots": [("chest", "main"), ("front_delts", "accessory"), ("triceps", "accessory")]},
        {"name_en": "Pull", "name_ro": "Tras", "slots": [("lats", "main"), ("rear_delts", "accessory"), ("biceps", "accessory")]},
        {"name_en": "Legs", "name_ro": "Picioare", "slots": [("quads", "main"), ("hamstrings", "accessory"), ("calves", "accessory")]},
    ]},
    "powerbuilding": {"emphasis": "powerbuilding", "days": [
        {"name_en": "Upper Power", "name_ro": "Superior Forță", "slots": [("chest", "main"), ("lats", "accessory"), ("triceps", "accessory")]},
        {"name_en": "Lower Power", "name_ro": "Inferior Forță", "slots": [("quads", "main"), ("hamstrings", "accessory"), ("core", "accessory")]},
        {"name_en": "Upper Volume", "name_ro": "Superior Volum", "slots": [("front_delts", "main"), ("lats", "main"), ("biceps", "accessory")]},
        {"name_en": "Lower Volume", "name_ro": "Inferior Volum", "slots": [("hamstrings", "main"), ("quads", "accessory"), ("calves", "accessory")]},
    ]},
    "bodyweight": {"emphasis": "bodyweight", "days": [
        {"name_en": "Bodyweight Full Body A", "name_ro": "Corp Întreg (fără echip.) A",
         "slots": [("chest", "main"), ("quads", "main"), ("lats", "main"), ("core", "accessory")]},
        {"name_en": "Bodyweight Full Body B", "name_ro": "Corp Întreg (fără echip.) B",
         "slots": [("hamstrings", "main"), ("chest", "accessory"), ("lats", "accessory"), ("core", "accessory")]},
    ]},
    "home": {"emphasis": "hypertrophy", "days": [
        {"name_en": "Home Upper", "name_ro": "Acasă - Superior", "slots": [("chest", "main"), ("lats", "main"), ("biceps", "accessory")]},
        {"name_en": "Home Lower", "name_ro": "Acasă - Inferior", "slots": [("quads", "main"), ("hamstrings", "accessory"), ("core", "accessory")]},
    ]},
    "custom": {"emphasis": "balanced", "days": []},
}

# how many training days to spread across the week, evenly, starting Monday
SPREAD_PATTERNS = {
    1: [0], 2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 3, 4],
    5: [0, 1, 2, 3, 4], 6: [0, 1, 2, 3, 4, 5], 7: [0, 1, 2, 3, 4, 5, 6],
}


def _effective_equipment(profile_equipment):
    return set(profile_equipment or []) | {"bodyweight"}


def _experience_ok(user_level, exercise_level):
    return EXPERIENCE_RANK.get(user_level, 1) >= EXPERIENCE_RANK.get(exercise_level, 1)


def _equipment_ok(equipment_available, exercise_equipment):
    if not exercise_equipment:
        return True
    return bool(set(exercise_equipment) & equipment_available) or "bodyweight" in exercise_equipment


def _injury_ok(injury_tags, exercise_avoid_tags):
    if not injury_tags or not exercise_avoid_tags:
        return True
    return not (set(injury_tags) & set(exercise_avoid_tags))


def filter_exercises(exercises, muscle=None, pattern=None, equipment=None,
                      experience_level="beginner", injury_tags=None, exclude_keys=None):
    """exercises: list of exercise dicts (from Exercise.__table__ columns).
    Returns the subset matching all the given criteria."""
    equipment_set = _effective_equipment(equipment)
    exclude_keys = exclude_keys or set()
    out = []
    for ex in exercises:
        if ex["key"] in exclude_keys:
            continue
        if muscle and ex["primary_muscle"] != muscle:
            continue
        if pattern and ex["movement_pattern"] != pattern:
            continue
        if not _equipment_ok(equipment_set, ex.get("equipment") or []):
            continue
        if not _experience_ok(experience_level, ex.get("experience_level", "beginner")):
            continue
        if not _injury_ok(injury_tags, ex.get("avoid_if_injury") or []):
            continue
        out.append(ex)
    return out


def _week_index(today=None):
    today = today or date.today()
    return today.isocalendar()[1]


def _pick_exercise(candidates, rotation_seed):
    if not candidates:
        return None
    return candidates[rotation_seed % len(candidates)]


def build_plan(exercises, profile_dict, chosen_weekdays, style, equipment=None,
               difficulty=None, today=None):
    """Build a full weekly plan (list of day dicts) for the given style and
    chosen training weekdays (list of 0=Mon..6=Sun ints, rest days implied).

    Returns: list of 7 day dicts: {weekday_index, is_rest, label, exercises:[...]}
    exercises: list of {exercise_key, sets, reps, order_index, is_main_lift}
    """
    config = STYLE_CONFIG.get(style, STYLE_CONFIG["upper_lower"])
    blueprints = config["days"]
    scheme = EMPHASIS_SCHEMES[config["emphasis"]]
    equipment = equipment if equipment is not None else profile_dict.get("equipment", [])
    experience_level = profile_dict.get("experience_level", "beginner")
    injury_tags = profile_dict.get("injury_tags", [])
    rotation_seed = _week_index(today)

    chosen_weekdays = sorted(set(chosen_weekdays))
    days_out = []
    used_keys_this_week = set()

    for idx in range(7):
        if idx not in chosen_weekdays or not blueprints:
            days_out.append({"weekday_index": idx, "is_rest": True, "label_en": "Rest",
                              "label_ro": "Odihnă", "exercises": []})
            continue

        blueprint = blueprints[chosen_weekdays.index(idx) % len(blueprints)]
        day_exercises = []
        for order, (muscle, role) in enumerate(blueprint["slots"]):
            candidates = filter_exercises(
                exercises, muscle=muscle, equipment=equipment,
                experience_level=experience_level, injury_tags=injury_tags,
                exclude_keys=used_keys_this_week,
            )
            picked = _pick_exercise(candidates, rotation_seed + order)
            if not picked:
                # relax: allow repeats within the week if the equipment/muscle pool is small
                candidates = filter_exercises(exercises, muscle=muscle, equipment=equipment,
                                               experience_level=experience_level, injury_tags=injury_tags)
                picked = _pick_exercise(candidates, rotation_seed + order)
            if not picked:
                continue
            sets, reps = scheme["main" if role == "main" else "accessory"]
            day_exercises.append({
                "exercise_key": picked["key"], "sets": sets, "reps": reps,
                "order_index": order, "is_main_lift": role == "main",
                "rest_seconds": 150 if role == "main" else 75,
                "warmup_sets": 2 if role == "main" else 0,
            })
            used_keys_this_week.add(picked["key"])

        days_out.append({
            "weekday_index": idx, "is_rest": False,
            "label_en": blueprint["name_en"], "label_ro": blueprint["name_ro"],
            "exercises": day_exercises,
        })

    return days_out


def default_plan_weekdays(training_days_per_week):
    n = max(1, min(7, int(training_days_per_week or 4)))
    return SPREAD_PATTERNS[n]


def get_phase(profile_dict, today=None):
    """Return-to-training ramp phase, generalized from v1: first 3 weeks
    after `return_to_training_start_date` prescribe lighter loads."""
    today = today or date.today()
    start_str = profile_dict.get("return_to_training_start_date")
    if not start_str:
        return "normal", None
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    days_in = max((today - start).days, 0)
    week_number = (days_in // 7) + 1
    if week_number <= 3:
        return "ramp", week_number
    return "normal", None


RAMP_PCT_BY_WEEK = {1: 0.70, 2: 0.80, 3: 0.85}


def ramp_weight(target_weight_kg, week_number):
    if target_weight_kg is None:
        return None
    pct = RAMP_PCT_BY_WEEK.get(week_number, 0.85)
    return round(target_weight_kg * pct, 1)


# ---------------------------------------------------------------------------
# Exercise replacement
# ---------------------------------------------------------------------------

def suggest_replacements(exercises, current_key, profile_dict, limit=6):
    """Returns {"recommended": [...], "same_muscle": [...], "same_pattern": [...]}."""
    current = next((e for e in exercises if e["key"] == current_key), None)
    if not current:
        return {"recommended": [], "same_muscle": [], "same_pattern": []}

    equipment = profile_dict.get("equipment", [])
    experience_level = profile_dict.get("experience_level", "beginner")
    injury_tags = profile_dict.get("injury_tags", [])

    same_muscle = filter_exercises(
        exercises, muscle=current["primary_muscle"], equipment=equipment,
        experience_level=experience_level, injury_tags=injury_tags,
        exclude_keys={current_key},
    )
    same_pattern = filter_exercises(
        exercises, pattern=current["movement_pattern"], equipment=equipment,
        experience_level=experience_level, injury_tags=injury_tags,
        exclude_keys={current_key} | {e["key"] for e in same_muscle},
    )

    recommended = (same_muscle + same_pattern)[:2]
    return {
        "recommended": recommended,
        "same_muscle": same_muscle[:limit],
        "same_pattern": same_pattern[:limit],
        "original": current,
    }


def replacement_explanation(original, replacement, lang="en"):
    same_muscle = original["primary_muscle"] == replacement["primary_muscle"]
    if lang == "ro":
        if same_muscle:
            return (f"Vizează același mușchi principal ({replacement['primary_muscle']}) ca "
                    f"{original['name_ro']}, folosind: {', '.join(replacement['equipment']) or 'greutate corporală'}.")
        return (f"Folosește tiparul de mișcare '{replacement['movement_pattern']}', similar cu "
                f"{original['name_ro']}, dar vizează {replacement['primary_muscle']}.")
    if same_muscle:
        return (f"Targets the same primary muscle ({replacement['primary_muscle']}) as "
                f"{original['name_en']}, using: {', '.join(replacement['equipment']) or 'bodyweight'}.")
    return (f"Uses the '{replacement['movement_pattern']}' movement pattern, similar to "
            f"{original['name_en']}, but targets {replacement['primary_muscle']}.")


# ---------------------------------------------------------------------------
# Logging analytics: e1RM, PRs, volume
# ---------------------------------------------------------------------------

def estimate_1rm(weight_kg, reps):
    """Epley formula. Reasonably accurate up to ~10 reps."""
    if not weight_kg or not reps:
        return 0
    if reps == 1:
        return round(weight_kg, 1)
    return round(weight_kg * (1 + reps / 30), 1)


def best_e1rm_for_exercise(set_logs, exercise_key, before_date=None):
    """set_logs: list of dicts with date/exercise_key/weight_kg/reps_done.
    Returns the best estimated 1RM logged for this exercise (optionally
    only sets before a given date, to check "is this session a new PR")."""
    best = 0
    for s in set_logs:
        if s["exercise_key"] != exercise_key:
            continue
        if before_date and s["date"] >= before_date:
            continue
        e1 = estimate_1rm(s.get("weight_kg"), s.get("reps_done"))
        best = max(best, e1)
    return best


def detect_pr(set_logs, new_set):
    """new_set: {"exercise_key","date","weight_kg","reps_done"}.
    Returns True if this set's estimated 1RM beats every prior logged set
    for the same exercise (before this date)."""
    new_e1 = estimate_1rm(new_set.get("weight_kg"), new_set.get("reps_done"))
    if new_e1 <= 0:
        return False
    prior_best = best_e1rm_for_exercise(set_logs, new_set["exercise_key"], before_date=new_set["date"])
    return new_e1 > prior_best


def volume_by_muscle(set_logs, exercises_by_key, since_date=None):
    """Total volume (sets x reps x weight) grouped by primary_muscle."""
    totals = {}
    for s in set_logs:
        if since_date and s["date"] < since_date:
            continue
        if s.get("is_warmup"):
            continue
        ex = exercises_by_key.get(s["exercise_key"])
        if not ex:
            continue
        muscle = ex["primary_muscle"]
        vol = (s.get("weight_kg") or 0) * (s.get("reps_done") or 0)
        totals[muscle] = totals.get(muscle, 0) + vol
    return totals
