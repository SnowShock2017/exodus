"""
nutrition_engine.py
--------------------
Calorie & macro targets, a small bilingual (EN/RO) list of meal ideas built
around foods that are cheap and easy to find in Romania, and the food-
logging math (looking up a food, scaling it by quantity, and totalling up
a day's logged entries against your targets).

Method for targets
-------------------
1. BMR via Mifflin-St Jeor (most accurate common formula, doesn't need
   body-fat %):
       men:  BMR = 10*weight_kg + 6.25*height_cm - 5*age + 5
2. TDEE = BMR * activity multiplier (based on training days/week + job).
3. Goal = "lean_maintain_strength" -> moderate ~18% deficit. Moderate
   (not aggressive) on purpose: aggressive cuts are the #1 cause of lost
   strength/muscle, which conflicts with the user's stated goal of
   keeping his lifts up while leaning out.
4. Protein set high (2.2 g/kg) to protect muscle/strength in a deficit.
   Fat set to a sensible floor (0.8 g/kg, hormones need dietary fat).
   Remaining calories -> carbs, which fuel the actual training sessions.
"""

from datetime import date, datetime, timedelta

from logic.profile_store import get_food_db

ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.35,
    "moderate": 1.55,   # 3-5 training days/week + normal daily life
    "high": 1.7,        # 4-5 hard sessions + physically active job
}

DEFICIT_BY_GOAL = {
    "lean_maintain_strength": 0.18,   # ~18% below maintenance
    "lean_aggressive": 0.25,
    "recomp": 0.10,
    "bulk": -0.10,  # negative deficit = surplus
}

MEAL_IDEAS = [
    {
        "en": "Greek yogurt + oats + honey + walnuts",
        "ro": "Iaurt grecesc + fulgi de ovăz + miere + nuci",
        "tag": "breakfast", "protein_note": "high protein, fast to make",
    },
    {
        "en": "Eggs (whole + extra whites) + whole-grain bread + tomatoes",
        "ro": "Ouă (întregi + albușuri extra) + pâine integrală + roșii",
        "tag": "breakfast", "protein_note": "classic, cheap, filling",
    },
    {
        "en": "Grilled chicken breast + rice + salad",
        "ro": "Piept de pui la grătar + orez + salată",
        "tag": "lunch_dinner", "protein_note": "the default 'can't go wrong' meal",
    },
    {
        "en": "Ground beef (5% fat) + potatoes + vegetables",
        "ro": "Carne tocată de vită (5% grăsime) + cartofi + legume",
        "tag": "lunch_dinner", "protein_note": "budget-friendly, very filling",
    },
    {
        "en": "Cottage cheese (branza de vaci) + rye bread + cucumber",
        "ro": "Brânză de vaci + pâine de secară + castraveți",
        "tag": "snack", "protein_note": "Romanian pantry staple, slow-digesting protein",
    },
    {
        "en": "Whey protein shake + banana",
        "ro": "Shake de proteine (whey) + banană",
        "tag": "snack", "protein_note": "use to close a protein gap post-workout",
    },
    {
        "en": "Salmon or trout + quinoa/rice + broccoli",
        "ro": "Somon sau păstrăv + quinoa/orez + broccoli",
        "tag": "lunch_dinner", "protein_note": "extra omega-3, good 1-2x/week",
    },
    {
        "en": "Turkey breast + sweet potato + green beans",
        "ro": "Piept de curcan + cartof dulce + fasole verde",
        "tag": "lunch_dinner", "protein_note": "very lean, easy to hit protein target",
    },
]

MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]


def calculate_targets(profile):
    weight = float(profile.get("weight_kg", 80))
    height = float(profile.get("height_cm", 175))
    age = int(profile.get("age", 25))
    sex = profile.get("sex", "male")
    activity = profile.get("activity_level", "moderate")
    goal = profile.get("goal", "lean_maintain_strength")

    if sex == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    multiplier = ACTIVITY_MULTIPLIERS.get(activity, 1.55)
    tdee = bmr * multiplier

    deficit_pct = DEFICIT_BY_GOAL.get(goal, 0.18)
    target_calories = tdee * (1 - deficit_pct)

    protein_g = round(2.2 * weight)
    fat_g = round(0.8 * weight)
    protein_kcal = protein_g * 4
    fat_kcal = fat_g * 9
    remaining_kcal = max(target_calories - protein_kcal - fat_kcal, 0)
    carb_g = round(remaining_kcal / 4)

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "target_calories": round(target_calories),
        "deficit_pct": round(deficit_pct * 100),
        "protein_g": protein_g,
        "fat_g": fat_g,
        "carb_g": carb_g,
    }


def get_meal_ideas(lang="en"):
    return MEAL_IDEAS


# ---------------------------------------------------------------------------
# Food logging
# ---------------------------------------------------------------------------

def find_food(name, lang="en"):
    """Match a food by its displayed name (either language) or its key."""
    if not name:
        return None
    name_lower = name.strip().lower()
    for food in get_food_db():
        if food["key"] == name_lower:
            return food
        if food["name_en"].lower() == name_lower:
            return food
        if food["name_ro"].lower() == name_lower:
            return food
    return None


def compute_macros(food, qty):
    """Scale a food_db entry's macros by quantity.

    unit == "g"    -> qty is grams, food values are per `per` grams (usually 100)
    unit == "unit" -> qty is a count (eggs, bananas, scoops), food values are per `per` units (usually 1)
    """
    qty = float(qty)
    factor = qty / float(food.get("per", 100))
    return {
        "kcal": round(food["kcal"] * factor),
        "protein_g": round(food["protein"] * factor, 1),
        "carb_g": round(food["carb"] * factor, 1),
        "fat_g": round(food["fat"] * factor, 1),
    }


def build_log_entry(food, qty, meal_type, lang="en"):
    macros = compute_macros(food, qty)
    return {
        "meal_type": meal_type,
        "food_key": food["key"],
        "food_name": food["name_ro"] if lang == "ro" else food["name_en"],
        "qty": qty,
        "unit": food["unit"],
        "kcal": macros["kcal"],
        "protein_g": macros["protein_g"],
        "carb_g": macros["carb_g"],
        "fat_g": macros["fat_g"],
    }


def entries_for_date(meal_log, target_date=None):
    target_date = target_date or date.today().isoformat()
    return [e for e in meal_log if e.get("date") == target_date]


def daily_totals(meal_log, target_date=None):
    entries = entries_for_date(meal_log, target_date)
    totals = {"kcal": 0, "protein_g": 0.0, "carb_g": 0.0, "fat_g": 0.0}
    for e in entries:
        totals["kcal"] += e.get("kcal", 0)
        totals["protein_g"] += e.get("protein_g", 0)
        totals["carb_g"] += e.get("carb_g", 0)
        totals["fat_g"] += e.get("fat_g", 0)
    totals["protein_g"] = round(totals["protein_g"], 1)
    totals["carb_g"] = round(totals["carb_g"], 1)
    totals["fat_g"] = round(totals["fat_g"], 1)
    return totals, entries


def progress_pct(logged, target):
    if not target:
        return 0
    return max(0, min(100, round((logged / target) * 100)))


def calorie_history(meal_log, days=14):
    """List of {"date", "kcal"} for the last `days` days, oldest first,
    including days with 0 logged (so the chart doesn't have gaps)."""
    today = date.today()
    by_date = {}
    for e in meal_log:
        d = e.get("date")
        by_date[d] = by_date.get(d, 0) + e.get("kcal", 0)
    history = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        history.append({"date": d, "kcal": by_date.get(d, 0)})
    return history
