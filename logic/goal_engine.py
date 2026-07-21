"""
goal_engine.py
--------------
The three goal modes and the calorie/macro math behind each, plus the
"gradual transition" logic: when a user switches goals, we don't jump
straight to the new calorie target — we ramp linearly over
GOAL_TRANSITION_DAYS so there's never a sudden, jarring calorie swing.

BMR: Mifflin-St Jeor (doesn't require body-fat % estimation, most widely
validated formula for a general population).
TDEE: BMR x activity multiplier.

Goal modes
----------
lean_maintain_strength  -> ~18% deficit, high protein (2.2 g/kg), moderate
                            fat (0.8 g/kg), rest carbs. Prioritizes keeping
                            strength/muscle while losing fat.
maintenance              -> ~0% deficit (right at TDEE), balanced macros
                            (1.8 g/kg protein, 0.9 g/kg fat, rest carbs).
muscle_gain               -> ~12% surplus, high protein (2.0 g/kg), higher
                            carbs to fuel training, moderate fat.

All deficits/surpluses are intentionally moderate — large swings are where
people lose strength on a cut or gain excess fat on a bulk. This mirrors
the "no extreme calorie changes" requirement directly.
"""

from datetime import date, datetime, timedelta

ACTIVITY_MULTIPLIERS = {"sedentary": 1.35, "moderate": 1.55, "high": 1.7}

GOAL_PARAMS = {
    "lean_maintain_strength": {"pct_adjust": -0.18, "protein_per_kg": 2.2, "fat_per_kg": 0.8},
    "maintenance": {"pct_adjust": 0.0, "protein_per_kg": 1.8, "fat_per_kg": 0.9},
    "muscle_gain": {"pct_adjust": 0.12, "protein_per_kg": 2.0, "fat_per_kg": 0.9},
}

GOAL_TRANSITION_DAYS = 10  # ramp calories linearly over this many days after a goal switch

FIBER_PER_1000KCAL = 14   # standard general guideline (~14g fiber / 1000 kcal)
WATER_ML_PER_KG = 35      # general baseline recommendation, +500ml on training days


def _bmr(profile):
    weight, height, age = profile.weight_kg, profile.height_cm, profile.age
    if profile.sex == "female":
        return 10 * weight + 6.25 * height - 5 * age - 161
    return 10 * weight + 6.25 * height - 5 * age + 5


def _tdee(profile):
    return _bmr(profile) * ACTIVITY_MULTIPLIERS.get(profile.activity_level, 1.55)


def _full_target_calories(profile, goal=None):
    goal = goal or profile.goal
    params = GOAL_PARAMS.get(goal, GOAL_PARAMS["lean_maintain_strength"])
    return _tdee(profile) * (1 + params["pct_adjust"])


def switch_goal(profile, new_goal, today=None):
    """Call this when the user picks a new goal. Sets up the gradual
    transition and returns an explanation string (bilingual dict)."""
    today = today or date.today()
    old_calories = round(_full_target_calories(profile))  # today's target under the OLD goal
    profile.goal = new_goal
    profile.goal_changed_at = today.isoformat()
    profile.goal_transition_from_calories = old_calories

    new_calories = round(_full_target_calories(profile))
    diff = new_calories - old_calories
    direction_en = "up" if diff > 0 else "down"
    direction_ro = "crescând" if diff > 0 else "scăzând"

    explanation_en = (
        f"Switched goal to {new_goal.replace('_', ' ')}. Calories will ramp {direction_en} "
        f"from ~{old_calories} to ~{new_calories} kcal/day over the next {GOAL_TRANSITION_DAYS} days, "
        f"not all at once — that avoids a jarring, sudden change."
    )
    explanation_ro = (
        f"Obiectiv schimbat în {new_goal.replace('_', ' ')}. Caloriile vor crește treptat "
        f"({direction_ro}) de la ~{old_calories} la ~{new_calories} kcal/zi în următoarele "
        f"{GOAL_TRANSITION_DAYS} zile, nu dintr-o dată — asta evită o schimbare bruscă."
    )
    return {"en": explanation_en, "ro": explanation_ro, "old_calories": old_calories, "new_calories": new_calories}


def _transitioned_target_calories(profile, today=None):
    """Today's actual calorie target, accounting for an in-progress ramp."""
    full_target = _full_target_calories(profile)
    if not profile.goal_changed_at or profile.goal_transition_from_calories is None:
        return full_target

    today = today or date.today()
    changed_at = datetime.strptime(profile.goal_changed_at, "%Y-%m-%d").date()
    days_in = (today - changed_at).days
    if days_in <= 0:
        return profile.goal_transition_from_calories
    if days_in >= GOAL_TRANSITION_DAYS:
        return full_target

    frac = days_in / GOAL_TRANSITION_DAYS
    return profile.goal_transition_from_calories + frac * (full_target - profile.goal_transition_from_calories)


def calculate_targets(profile, today=None):
    weight = profile.weight_kg
    params = GOAL_PARAMS.get(profile.goal, GOAL_PARAMS["lean_maintain_strength"])

    target_calories = round(_transitioned_target_calories(profile, today))
    protein_g = round(params["protein_per_kg"] * weight)
    fat_g = round(params["fat_per_kg"] * weight)
    protein_kcal = protein_g * 4
    fat_kcal = fat_g * 9
    remaining_kcal = max(target_calories - protein_kcal - fat_kcal, 0)
    carb_g = round(remaining_kcal / 4)

    fiber_g = round(target_calories / 1000 * FIBER_PER_1000KCAL)
    water_ml = round(weight * WATER_ML_PER_KG)

    in_transition = bool(
        profile.goal_changed_at and profile.goal_transition_from_calories is not None and
        (today or date.today()) < datetime.strptime(profile.goal_changed_at, "%Y-%m-%d").date()
        + timedelta(days=GOAL_TRANSITION_DAYS)
    )

    return {
        "bmr": round(_bmr(profile)),
        "tdee": round(_tdee(profile)),
        "target_calories": target_calories,
        "full_target_calories": round(_full_target_calories(profile)),
        "protein_g": protein_g,
        "carb_g": carb_g,
        "fat_g": fat_g,
        "fiber_g": fiber_g,
        "water_ml": water_ml,
        "in_transition": in_transition,
        "goal": profile.goal,
    }


GOAL_LABELS = {
    "lean_maintain_strength": {"en": "Fat Loss + Keep Strength", "ro": "Slăbire + Păstrarea Forței"},
    "maintenance": {"en": "Maintenance", "ro": "Menținere"},
    "muscle_gain": {"en": "Muscle Gain", "ro": "Creștere Musculară"},
}

GOAL_DESCRIPTIONS = {
    "lean_maintain_strength": {
        "en": "Controlled calorie deficit, high protein, prioritizes fat loss while keeping your strength and muscle.",
        "ro": "Deficit caloric controlat, proteine ridicate, prioritizează pierderea de grăsime păstrând forța și mușchii.",
    },
    "maintenance": {
        "en": "Calories near maintenance, balanced macros, stable energy and performance.",
        "ro": "Calorii aproape de menținere, macronutrienți echilibrați, energie și performanță stabile.",
    },
    "muscle_gain": {
        "en": "Controlled calorie surplus, high protein and carbs, prioritizes muscle and strength gain.",
        "ro": "Surplus caloric controlat, proteine și carbohidrați ridicați, prioritizează creșterea musculară și de forță.",
    },
}
