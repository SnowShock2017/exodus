"""
cache.py
--------
The four "shared library" tables — Exercise, MealTemplate, FoodItem,
CrossfitWorkout — are identical for every user and only ever change when
the seed_data/*.json files are edited and the app is redeployed. Every
user reads them, nobody writes to them.

Before this module existed, nearly every route queried these tables fresh
on every single request (often with `Exercise.query.filter_by(key=...).first()`
called once per exercise *inside a Python loop* — a classic N+1 pattern).
Each of those is a real network round trip to the Postgres database, and
on a free-tier host that round trip can be tens to hundreds of
milliseconds — so a page that used to fire 10-20 of these sequentially
could easily take a few seconds to respond, which is exactly the
page-to-page lag this module fixes.

This module loads each table into memory once per running server process
and serves every read after that from a plain Python dict — zero
additional database round trips. Since the data can't change without a
fresh deploy (which starts a new process with an empty cache), this is
safe with no staleness risk in normal use. If you ever add an in-app way
to edit the shared library while the server is running, call `clear()`
afterward to force a reload.
"""

from models import Exercise, MealTemplate, FoodItem, CrossfitWorkout
from logic.helpers import exercise_to_dict, meal_to_dict, food_to_dict, crossfit_to_dict

_cache = {}


def _load(name, query_all, to_dict):
    if name not in _cache:
        items = [to_dict(r) for r in query_all()]
        _cache[name] = {"list": items, "by_key": {i["key"]: i for i in items}}
    return _cache[name]


def get_exercises():
    return _load("exercises", lambda: Exercise.query.all(), exercise_to_dict)["list"]


def get_exercise_by_key(key):
    return _load("exercises", lambda: Exercise.query.all(), exercise_to_dict)["by_key"].get(key)


def get_meals():
    return _load("meals", lambda: MealTemplate.query.all(), meal_to_dict)["list"]


def get_meal_by_key(key):
    return _load("meals", lambda: MealTemplate.query.all(), meal_to_dict)["by_key"].get(key)


def get_foods():
    return _load("foods", lambda: FoodItem.query.all(), food_to_dict)["list"]


def get_food_by_key(key):
    return _load("foods", lambda: FoodItem.query.all(), food_to_dict)["by_key"].get(key)


def get_crossfit_workouts():
    return _load("crossfit", lambda: CrossfitWorkout.query.all(), crossfit_to_dict)["list"]


def get_crossfit_by_key(key):
    return _load("crossfit", lambda: CrossfitWorkout.query.all(), crossfit_to_dict)["by_key"].get(key)


def clear():
    """Force every cached table to reload from the database on next access.
    Not needed after a normal redeploy (new process = empty cache already);
    only useful if you add live content editing without restarting."""
    _cache.clear()
