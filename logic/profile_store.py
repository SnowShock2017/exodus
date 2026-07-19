"""
profile_store.py
-----------------
Tiny JSON-file "database" for a single-user app. No SQL, no server —
just reads/writes JSON files in the data/ folder. Good enough for one
person's data, easy to inspect/edit by hand if needed.

Files used
----------
data/user_profile.json  -> one dict: stats, goal, PRs, language, etc.
data/weight_log.json    -> list of {"date": "YYYY-MM-DD", "weight_kg": float}
data/workout_log.json   -> list of {"date", "day_name", "exercise", "weight_kg",
                                     "reps_done": [..], "rpe": float or null}
data/meal_log.json      -> list of {"date", "compliant": bool, "note": str}
"""

import json
import os
from datetime import date

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

PROFILE_PATH = os.path.join(DATA_DIR, "user_profile.json")
WEIGHT_LOG_PATH = os.path.join(DATA_DIR, "weight_log.json")
WORKOUT_LOG_PATH = os.path.join(DATA_DIR, "workout_log.json")
MEAL_LOG_PATH = os.path.join(DATA_DIR, "meal_log.json")


def _read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return default
        return json.loads(content)


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_profile():
    return _read_json(PROFILE_PATH, {})


def save_profile(profile):
    _write_json(PROFILE_PATH, profile)


def update_profile(**kwargs):
    profile = get_profile()
    profile.update(kwargs)
    save_profile(profile)
    return profile


def get_weight_log():
    return _read_json(WEIGHT_LOG_PATH, [])


def add_weight_entry(weight_kg, log_date=None):
    log = get_weight_log()
    log.append({"date": log_date or date.today().isoformat(), "weight_kg": float(weight_kg)})
    _write_json(WEIGHT_LOG_PATH, log)
    # keep the profile's "current" weight in sync so nutrition/workout
    # calculations always use the latest number
    update_profile(weight_kg=float(weight_kg))
    return log


def get_workout_log():
    return _read_json(WORKOUT_LOG_PATH, [])


def add_workout_entries(entries):
    """entries: list of dicts, see module docstring for shape."""
    log = get_workout_log()
    log.extend(entries)
    _write_json(WORKOUT_LOG_PATH, log)
    return log


def get_meal_log():
    return _read_json(MEAL_LOG_PATH, [])


def add_meal_entry(entry):
    log = get_meal_log()
    log.append(entry)
    _write_json(MEAL_LOG_PATH, log)
    return log
