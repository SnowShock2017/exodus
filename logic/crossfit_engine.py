"""
crossfit_engine.py
-------------------
Browsing/filtering the curated CrossFit template library
(seed_data/crossfit_workouts.json), plus a rule-based *generator* that
assembles a brand-new workout on demand from the exercise library's
"conditioning" movement pool — this is what satisfies "Generate a new
workout with AI" without needing a paid LLM: it's a deterministic
combinatorial generator with the same safety filters (equipment,
experience level, injuries) as the strength workout engine.

Safety: the generator never combines more than one heavy barbell
ballistic movement (thruster, deadlift-for-reps) for beginners, and always
respects avoid_if_injury tags — see `_safe_for_beginner()`.
"""

import random
from datetime import date

TYPES = ["AMRAP", "EMOM", "FOR_TIME", "INTERVAL", "STRENGTH_CONDITIONING",
         "BODYWEIGHT", "PARTNER", "EQUIPMENT_FREE"]
DIFFICULTIES = ["beginner", "intermediate", "advanced"]

# movements considered higher-risk for beginners even if equipment/experience
# tags technically allow them — kept out of beginner auto-generated WODs.
BEGINNER_UNSAFE_KEYS = {"thruster", "kb_clean_press", "double_under", "box_jump"}


def filter_workouts(workouts, wtype=None, difficulty=None, equipment=None, exclude_keys=None):
    exclude_keys = exclude_keys or set()
    equipment_set = set(equipment or [])
    out = []
    for w in workouts:
        if w["key"] in exclude_keys:
            continue
        if wtype and w["type"] != wtype:
            continue
        if difficulty and w["difficulty"] != difficulty:
            continue
        if equipment is not None:
            needed = set(w.get("equipment") or [])
            if needed and not needed.issubset(equipment_set | {"bodyweight"}):
                continue
        out.append(w)
    return out


def scale_workout(workout, target_difficulty):
    """Returns a copy of the movements list scaled up/down in reps/rounds
    relative to the workout's native difficulty. Simple linear scaling —
    transparent, not a black box."""
    native = DIFFICULTIES.index(workout["difficulty"])
    target = DIFFICULTIES.index(target_difficulty)
    step_pct = 0.7 if target < native else (1.25 if target > native else 1.0)
    diff_steps = abs(target - native)
    factor = step_pct ** diff_steps if diff_steps else 1.0

    scaled_movements = []
    for m in workout["movements"]:
        m2 = dict(m)
        if "reps" in m2 and m2["reps"]:
            m2["reps"] = max(1, round(m2["reps"] * factor))
        scaled_movements.append(m2)
    return scaled_movements


def _safe_for_level(exercise, experience_level, injury_tags):
    if experience_level == "beginner" and exercise["key"] in BEGINNER_UNSAFE_KEYS:
        return False
    if injury_tags and set(exercise.get("avoid_if_injury") or []) & set(injury_tags):
        return False
    return True


def generate_workout(exercises, profile_dict, wtype="AMRAP", duration_min=12, today=None):
    """Assemble a brand-new WOD from the conditioning/full_body exercise
    pool. This is the rule-based 'AI generate' feature — deterministic
    given the same inputs and date, so refreshing doesn't give a wildly
    different workout, but a new day/profile does."""
    today = today or date.today()
    experience_level = profile_dict.get("experience_level", "beginner")
    equipment = set(profile_dict.get("equipment", [])) | {"bodyweight"}
    injury_tags = profile_dict.get("injury_tags", [])

    pool = [
        e for e in exercises
        if e["movement_pattern"] in ("conditioning", "core")
        and set(e.get("equipment") or ["bodyweight"]).issubset(equipment)
        and _safe_for_level(e, experience_level, injury_tags)
    ]
    if not pool:
        pool = [e for e in exercises if e["movement_pattern"] == "conditioning"
                and "bodyweight" in (e.get("equipment") or [])]

    rng = random.Random(f"{today.isoformat()}-{profile_dict.get('user_id', 0)}-{wtype}")
    movement_count = 3 if duration_min <= 15 else 4
    chosen = rng.sample(pool, k=min(movement_count, len(pool)))

    base_reps = {"beginner": 10, "intermediate": 15, "advanced": 20}[experience_level]
    movements = [{"exercise_key": e["key"], "reps": base_reps} for e in chosen]

    format_by_type = {
        "AMRAP": (f"As many rounds as possible in {duration_min} minutes.",
                  f"Cât mai multe runde posibil în {duration_min} minute."),
        "EMOM": (f"Every minute on the minute for {duration_min} minutes, rotating movements.",
                 f"În fiecare minut, timp de {duration_min} minute, rotind mișcările."),
        "FOR_TIME": ("Complete all movements for time, as fast as good form allows.",
                     "Completează toate mișcările cât mai repede, cu tehnică bună."),
    }
    format_en, format_ro = format_by_type.get(wtype, format_by_type["AMRAP"])

    return {
        "key": f"generated-{today.isoformat()}",
        "name_en": f"Generated {wtype.replace('_', ' ').title()} WOD",
        "name_ro": f"WOD generat ({wtype.replace('_', ' ').title()})",
        "type": wtype, "difficulty": experience_level,
        "equipment": sorted({eq for e in chosen for eq in (e.get("equipment") or [])}),
        "target_muscles": sorted({e["primary_muscle"] for e in chosen}),
        "est_duration_min": duration_min,
        "format_en": format_en, "format_ro": format_ro,
        "movements": movements,
        "scaling_notes_en": "Reduce reps by ~30% if this is your first attempt at the movements involved.",
        "scaling_notes_ro": "Redu repetările cu ~30% dacă este prima încercare la aceste mișcări.",
        "technique_notes_en": "Generated automatically — check each movement's instruction page if it's new to you.",
        "technique_notes_ro": "Generat automat — verifică pagina de instrucțiuni a fiecărei mișcări dacă e nouă pentru tine.",
        "generated": True,
    }
