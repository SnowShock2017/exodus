"""
helpers.py
----------
Converts SQLAlchemy model rows into the plain dicts every logic/*.py
engine expects (those modules are deliberately framework-free so they're
unit-testable — see their docstrings). Every route handler uses these
before calling into an engine, and never passes a raw model instance into
one of the logic/ modules.
"""


def row_to_dict(row, columns):
    return {c: getattr(row, c) for c in columns}


def profile_to_dict(profile):
    return {
        "user_id": profile.user_id,
        "name": profile.name, "age": profile.age, "sex": profile.sex,
        "height_cm": profile.height_cm, "weight_kg": profile.weight_kg,
        "target_weight_kg": profile.target_weight_kg, "goal": profile.goal,
        "experience_level": profile.experience_level, "activity_level": profile.activity_level,
        "training_days_per_week": profile.training_days_per_week,
        "preferred_style": profile.preferred_style, "equipment": profile.equipment or [],
        "dietary_prefs": profile.dietary_prefs or [], "allergies": profile.allergies or [],
        "dislikes": profile.dislikes or [], "injuries": profile.injuries,
        "injury_tags": profile.injury_tags or [], "language": profile.language,
        "units": profile.units, "meal_frequency": profile.meal_frequency,
        "sleep_hours": profile.sleep_hours, "step_target": profile.step_target,
        "prs_kg": profile.prs_kg or {}, "return_to_training_start_date": profile.return_to_training_start_date,
        "goal_changed_at": profile.goal_changed_at,
        "goal_transition_from_calories": profile.goal_transition_from_calories,
    }


EXERCISE_COLUMNS = ["key", "name_en", "name_ro", "primary_muscle", "secondary_muscles",
                     "equipment", "movement_pattern", "experience_level", "unilateral",
                     "instructions_en", "instructions_ro", "breathing_en", "breathing_ro",
                     "common_mistakes_en", "common_mistakes_ro", "safety_tips_en", "safety_tips_ro",
                     "easier_variation", "harder_variation", "avoid_if_injury"]

MEAL_COLUMNS = ["key", "name_en", "name_ro", "tags", "base_servings", "prep_time_min",
                 "difficulty", "ingredients", "kcal_per_serving", "protein_g_per_serving",
                 "carb_g_per_serving", "fat_g_per_serving", "fiber_g_per_serving",
                 "substitutions_en", "substitutions_ro", "steps_en", "steps_ro"]

FOOD_COLUMNS = ["key", "name_en", "name_ro", "unit", "per", "kcal", "protein", "carb", "fat", "fiber"]

CROSSFIT_COLUMNS = ["key", "name_en", "name_ro", "type", "difficulty", "equipment",
                     "target_muscles", "est_duration_min", "format_en", "format_ro",
                     "movements", "scaling_notes_en", "scaling_notes_ro",
                     "technique_notes_en", "technique_notes_ro"]

SET_LOG_COLUMNS = ["id", "date", "exercise_key", "weight_kg", "reps_done", "rpe", "rir",
                    "is_warmup", "completed", "notes", "pain"]

MEAL_LOG_COLUMNS = ["id", "date", "meal_type", "food_key", "food_name", "qty", "unit",
                     "kcal", "protein_g", "carb_g", "fat_g", "fiber_g", "source", "estimated"]


def exercise_to_dict(row):
    return row_to_dict(row, EXERCISE_COLUMNS)


def meal_to_dict(row):
    return row_to_dict(row, MEAL_COLUMNS)


def food_to_dict(row):
    return row_to_dict(row, FOOD_COLUMNS)


def crossfit_to_dict(row):
    return row_to_dict(row, CROSSFIT_COLUMNS)


def set_log_to_dict(row):
    return row_to_dict(row, SET_LOG_COLUMNS)


def meal_log_to_dict(row):
    return row_to_dict(row, MEAL_LOG_COLUMNS)
