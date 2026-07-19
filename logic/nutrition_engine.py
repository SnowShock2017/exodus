"""
nutrition_engine.py
--------------------
Calorie & macro targets, plus a small bilingual (EN/RO) list of meal ideas
built around foods that are cheap and easy to find in Romania.

Method
------
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
