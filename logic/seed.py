"""
seed.py
-------
Loads the shared library tables (exercises, meal templates, food items,
CrossFit workouts) from the JSON files in seed_data/ into the database,
but only if those tables are empty. Safe to call on every app startup —
it's a no-op after the first run.

Where to add more content
--------------------------
Edit the JSON files in seed_data/ (see DOCUMENTATION.md for the exact
schema of each), then either wipe the relevant table or call
`reseed_all(force=True)` once to reload everything.
"""

import json
import os

from extensions import db
from models import Exercise, MealTemplate, FoodItem, CrossfitWorkout

SEED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "seed_data")


def _load_json(filename):
    path = os.path.join(SEED_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_exercises(force=False):
    if not force and Exercise.query.first():
        return 0
    if force:
        Exercise.query.delete()
    rows = _load_json("exercises.json")
    for r in rows:
        db.session.add(Exercise(**r))
    db.session.commit()
    return len(rows)


def seed_meals(force=False):
    if not force and MealTemplate.query.first():
        return 0
    if force:
        MealTemplate.query.delete()
    rows = _load_json("meals.json")
    for r in rows:
        db.session.add(MealTemplate(**r))
    db.session.commit()
    return len(rows)


def seed_food_items(force=False):
    if not force and FoodItem.query.first():
        return 0
    if force:
        FoodItem.query.delete()
    rows = _load_json("food_db.json")
    for r in rows:
        db.session.add(FoodItem(**r))
    db.session.commit()
    return len(rows)


def seed_crossfit(force=False):
    if not force and CrossfitWorkout.query.first():
        return 0
    if force:
        CrossfitWorkout.query.delete()
    rows = _load_json("crossfit_workouts.json")
    for r in rows:
        db.session.add(CrossfitWorkout(**r))
    db.session.commit()
    return len(rows)


def seed_all(force=False):
    counts = {
        "exercises": seed_exercises(force),
        "meals": seed_meals(force),
        "food_items": seed_food_items(force),
        "crossfit_workouts": seed_crossfit(force),
    }
    return counts
