"""
nutrition_engine.py (v2 — multi-user)
---------------------------------------
Food-logging math, meal-template filtering/scaling, and shopping-list
generation. Framework-free (plain dicts in, plain dicts out) so it's
directly unit-testable; routes/meals.py wires it to the database.

Calorie/macro *targets* (BMR/TDEE/goal math) live in goal_engine.py — this
file is about logging what was actually eaten and browsing/using the meal
library, not about setting targets.
"""

from datetime import date, timedelta

MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]

# categories a meal can be filtered/tagged by — matches the tags used in
# seed_data/meals.json
MEAL_TAGS = [
    "breakfast", "lunch", "dinner", "snack", "pre_workout", "post_workout",
    "high_protein", "low_calorie", "budget", "quick", "romanian", "meal_prep",
    "vegetarian", "vegan", "lactose_free", "gluten_free", "high_carb",
    "low_carb", "dessert",
]

SHOPPING_CATEGORIES = {
    # crude food_key -> aisle category mapping for the shopping list grouping
    "chicken_breast": "meat", "ground_beef": "meat", "turkey_breast": "meat", "salmon": "meat",
    "white_rice": "pantry", "potatoes": "produce", "sweet_potato": "produce", "oats": "pantry",
    "quinoa": "pantry", "honey": "pantry", "olive_oil": "pantry", "mamaliga": "pantry",
    "greek_yogurt": "dairy", "cottage_cheese": "dairy", "telemea": "dairy",
    "whole_egg": "dairy", "egg_white": "dairy", "whey_protein": "supplements",
    "wholegrain_bread": "bakery", "rye_bread": "bakery",
    "banana": "produce", "broccoli": "produce", "green_beans": "produce",
    "tomatoes": "produce", "cucumber": "produce", "walnuts": "pantry",
}


# ---------------------------------------------------------------------------
# Food logging (simple food_db items, per 100g/unit)
# ---------------------------------------------------------------------------

def find_food(food_items, name_or_key, lang="en"):
    if not name_or_key:
        return None
    q = name_or_key.strip().lower()
    for f in food_items:
        if f["key"] == q or f["name_en"].lower() == q or f["name_ro"].lower() == q:
            return f
    return None


def compute_macros(food, qty):
    qty = float(qty)
    factor = qty / float(food.get("per", 100) or 100)
    return {
        "kcal": round(food["kcal"] * factor),
        "protein_g": round(food["protein"] * factor, 1),
        "carb_g": round(food["carb"] * factor, 1),
        "fat_g": round(food["fat"] * factor, 1),
        "fiber_g": round((food.get("fiber") or 0) * factor, 1),
    }


def build_log_entry(food, qty, meal_type, lang="en", source="db", barcode=None, estimated=False):
    macros = compute_macros(food, qty)
    return {
        "meal_type": meal_type,
        "food_key": food.get("key"),
        "food_name": food["name_ro"] if lang == "ro" else food["name_en"],
        "qty": qty, "unit": food["unit"],
        "source": source, "barcode": barcode, "estimated": estimated,
        **macros,
    }


def daily_totals(entries):
    totals = {"kcal": 0, "protein_g": 0.0, "carb_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0}
    for e in entries:
        totals["kcal"] += e.get("kcal", 0)
        totals["protein_g"] += e.get("protein_g", 0) or 0
        totals["carb_g"] += e.get("carb_g", 0) or 0
        totals["fat_g"] += e.get("fat_g", 0) or 0
        totals["fiber_g"] += e.get("fiber_g", 0) or 0
    for k in ("protein_g", "carb_g", "fat_g", "fiber_g"):
        totals[k] = round(totals[k], 1)
    return totals


def progress_pct(logged, target):
    if not target:
        return 0
    return max(0, min(150, round((logged / target) * 100)))


def calorie_history(entries_by_date, days=14):
    """entries_by_date: dict date-> list of log entry dicts (already grouped)."""
    today = date.today()
    out = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        day_entries = entries_by_date.get(d, [])
        out.append({"date": d, "kcal": sum(e.get("kcal", 0) for e in day_entries)})
    return out


# ---------------------------------------------------------------------------
# Meal template browsing / filtering / scaling
# ---------------------------------------------------------------------------

def filter_meals(meals, tags=None, max_kcal=None, min_protein=None, max_prep_min=None,
                  difficulty=None, exclude_keys=None):
    exclude_keys = exclude_keys or set()
    out = []
    for m in meals:
        if m["key"] in exclude_keys:
            continue
        if tags and not set(tags).issubset(set(m.get("tags", []))):
            continue
        if max_kcal and m["kcal_per_serving"] > max_kcal:
            continue
        if min_protein and m["protein_g_per_serving"] < min_protein:
            continue
        if max_prep_min and m["prep_time_min"] > max_prep_min:
            continue
        if difficulty and m["difficulty"] != difficulty:
            continue
        out.append(m)
    return out


def scale_meal(meal, servings):
    """Recompute ingredient quantities and macros for a different number of
    servings than the recipe's base_servings. Never mutates the original."""
    ratio = float(servings) / float(meal.get("base_servings", 1) or 1)
    scaled_ingredients = [
        {**ing, "qty": round(ing["qty"] * ratio, 1)} for ing in meal.get("ingredients", [])
    ]
    return {
        "servings": servings,
        "ingredients": scaled_ingredients,
        "kcal_total": round(meal["kcal_per_serving"] * servings),
        "protein_g_total": round(meal["protein_g_per_serving"] * servings, 1),
        "carb_g_total": round(meal["carb_g_per_serving"] * servings, 1),
        "fat_g_total": round(meal["fat_g_per_serving"] * servings, 1),
        "fiber_g_total": round(meal.get("fiber_g_per_serving", 0) * servings, 1),
        # per-serving values stay the same regardless of how many servings you make
        "kcal_per_serving": meal["kcal_per_serving"],
        "protein_g_per_serving": meal["protein_g_per_serving"],
    }


def recently_eaten_meal_keys(meal_log_entries, days=5):
    """food_key values logged in the last N days — used to avoid suggesting
    the same meals/foods over and over."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return {e["food_key"] for e in meal_log_entries if e.get("date", "") >= cutoff and e.get("food_key")}


def suggest_meals_for_remaining(meals, remaining_kcal, remaining_protein_g, tags=None,
                                 recently_used_keys=None, limit=6, target_kcal=None):
    """Simple rule-based 'what should I eat' suggestion: meals that fit
    within the remaining calorie budget and help close the protein gap,
    deprioritizing anything eaten in the last few days.

    target_kcal: the ideal size for this specific meal (e.g. a quarter of
    the day's remaining budget), if known. Without this, scoring purely by
    protein content tends to always pick the smallest high-protein meal in
    the library, which systematically undershoots the day's calorie target
    by a wide margin once you add up 3-4 "smallest possible" meals — see
    suggest_day_plan(), which is what actually hit this bug in practice.
    """
    recently_used_keys = recently_used_keys or set()
    candidates = filter_meals(meals, tags=tags)
    candidates = [m for m in candidates if m["kcal_per_serving"] <= max(remaining_kcal, 200)]
    ideal_kcal = target_kcal if target_kcal is not None else remaining_kcal

    def score(m):
        protein_fit = min(m["protein_g_per_serving"], remaining_protein_g)
        kcal_diff = abs(m["kcal_per_serving"] - ideal_kcal)
        closeness_to_ideal_size = max(0.0, 100.0 - kcal_diff / 5.0)
        penalty = 50 if m["key"] in recently_used_keys else 0
        return protein_fit + closeness_to_ideal_size - penalty

    candidates.sort(key=score, reverse=True)
    return candidates[:limit]


def suggest_day_plan(meals, target_calories, target_protein_g, recently_used_keys=None,
                      meal_types=None, max_servings=3):
    """Build a full day's suggested meals — one entry per meal-type slot,
    each possibly scaled to more than one serving — so the suggested day
    actually adds up close to the day's calorie/protein targets, instead of
    handing back a single default-size serving per slot regardless of how
    big the target is (that version could fall ~1000kcal short of a 3000kcal
    target, which is exactly the bug this replaced).

    Returns a list of meal dicts, each with the usual meal fields plus
    "slot", "servings", "kcal_total", and "protein_g_total" for the scaled
    amount actually suggested.
    """
    meal_types = meal_types or MEAL_TYPES
    recently_used_keys = set(recently_used_keys or set())
    remaining_kcal = target_calories
    remaining_protein = target_protein_g
    used_keys = set()
    plan = []
    n_slots = len(meal_types) or 1

    for i, slot in enumerate(meal_types):
        slots_left = n_slots - i
        target_kcal_slot = max(remaining_kcal / slots_left, 200)
        tags = [slot] if slot != "snack" else None

        candidates = suggest_meals_for_remaining(
            meals, remaining_kcal, remaining_protein, tags=tags,
            recently_used_keys=recently_used_keys | used_keys, limit=1, target_kcal=target_kcal_slot)
        if not candidates:
            candidates = suggest_meals_for_remaining(
                meals, remaining_kcal, remaining_protein,
                recently_used_keys=recently_used_keys | used_keys, limit=1, target_kcal=target_kcal_slot)
        if not candidates:
            continue

        m = candidates[0]
        servings = 1
        if m["kcal_per_serving"]:
            servings = max(1, round(target_kcal_slot / m["kcal_per_serving"]))
        servings = min(servings, max_servings)

        kcal_total = round(m["kcal_per_serving"] * servings)
        protein_total = round(m["protein_g_per_serving"] * servings, 1)

        plan.append({**m, "slot": slot, "servings": servings,
                     "kcal_total": kcal_total, "protein_g_total": protein_total})
        used_keys.add(m["key"])
        remaining_kcal -= kcal_total
        remaining_protein -= protein_total

    return plan


# ---------------------------------------------------------------------------
# Shopping list generation
# ---------------------------------------------------------------------------

def generate_shopping_list(meals_with_servings, have_at_home_keys=None):
    """meals_with_servings: list of (meal_dict, servings) tuples.
    Combines duplicate ingredients across meals, sums quantities, groups by
    category. have_at_home_keys: food_keys the user says they already have
    (marks those items pre-checked as 'have_at_home')."""
    have_at_home_keys = have_at_home_keys or set()
    combined = {}
    for meal, servings in meals_with_servings:
        scaled = scale_meal(meal, servings)
        for ing in scaled["ingredients"]:
            key = ing["food_key"]
            if key not in combined:
                combined[key] = {
                    "food_key": key, "name_en": ing["name_en"], "name_ro": ing["name_ro"],
                    "qty": 0, "unit": ing["unit"],
                    "category": SHOPPING_CATEGORIES.get(key, "other"),
                    "have_at_home": key in have_at_home_keys,
                }
            combined[key]["qty"] += ing["qty"]

    for item in combined.values():
        item["qty"] = round(item["qty"], 1)

    items = list(combined.values())
    items.sort(key=lambda i: (i["category"], i["name_en"]))
    return items
