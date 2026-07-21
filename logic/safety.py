"""
safety.py
---------
Two things live here:

1. Red-flag detection: keyword screening (EN+RO) for messages that
   describe potentially dangerous symptoms. When matched, every other
   engine (assistant, readiness) shows a "please see a medical
   professional" message INSTEAD of normal coaching output — this app
   must never try to diagnose or coach through those situations.

2. Readiness check-in logic: turns a quick pre-workout survey (energy,
   sleep quality, soreness, stress, available time, pain) into a
   suggested adjustment. The user always makes the final call — this only
   ever *suggests*.
"""

RED_FLAG_KEYWORDS_EN = [
    "chest pain", "can't breathe", "cannot breathe", "difficulty breathing",
    "fainted", "fainting", "passed out", "severe pain", "numbness in my arm",
    "not eating", "starving myself", "haven't eaten in days", "purge", "purging",
    "extremely dizzy", "blood in my", "can't stop throwing up",
]
RED_FLAG_KEYWORDS_RO = [
    "durere în piept", "dureri în piept", "nu pot respira", "dificultăți de respirație",
    "greu să respir", "leșin", "am leșinat", "durere severă", "dureri severe",
    "amorțeală în braț", "amorțeală pe braț", "nu mănânc", "nu am mâncat de zile",
    "amețeală extremă", "amețeli extreme", "sânge în", "nu mă pot opri din vărsat",
]

SAFETY_MESSAGE_EN = (
    "This sounds like it could be serious. I'm not able to give medical advice — "
    "please contact a doctor or emergency services if this is urgent. "
    "I can still help with training/nutrition questions once you've had this checked out."
)
SAFETY_MESSAGE_RO = (
    "Asta sună ca ar putea fi ceva serios. Nu pot oferi sfaturi medicale — "
    "te rog contactează un medic sau serviciile de urgență dacă e ceva urgent. "
    "Pot să te ajut în continuare cu întrebări despre antrenament/nutriție după ce verifici asta."
)


def check_red_flags(text):
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in RED_FLAG_KEYWORDS_EN) or any(k in t for k in RED_FLAG_KEYWORDS_RO)


def check_low_calorie_intake(logged_kcal, bmr):
    """Flags dangerously low intake: under 1200kcal absolute floor, or
    under 60% of BMR — either is a recognized marker of an unsafe deficit."""
    if logged_kcal <= 0:
        return False
    return logged_kcal < 1200 or logged_kcal < bmr * 0.6


LOW_CALORIE_WARNING_EN = (
    "Today's logged intake looks very low relative to what your body needs at rest. "
    "Chronic very-low-calorie eating risks losing muscle, metabolic slowdown, and other "
    "health issues. If this wasn't intentional, consider eating more; if you're "
    "restricting intentionally beyond the app's targets, please talk to a doctor or "
    "registered dietitian."
)
LOW_CALORIE_WARNING_RO = (
    "Consumul înregistrat azi pare foarte scăzut față de ce are nevoie corpul tău în repaus. "
    "Alimentația cronică cu foarte puține calorii riscă pierderea de mușchi, încetinirea "
    "metabolismului și alte probleme de sănătate. Dacă nu a fost intenționat, ia în calcul "
    "să mănânci mai mult; dacă restricționezi intenționat peste țintele aplicației, "
    "discută cu un medic sau nutriționist."
)


def suggest_readiness_action(energy, sleep_quality, soreness, stress, available_minutes,
                              planned_minutes=60, pain_notes=""):
    """Returns {"action": ..., "reason_en":..., "reason_ro":...}.
    action in: as_planned | reduce_weight | reduce_sets | lighter_workout | rest_day
    """
    if check_red_flags(pain_notes):
        return {"action": "rest_day", "safety_flag": True,
                "reason_en": SAFETY_MESSAGE_EN, "reason_ro": SAFETY_MESSAGE_RO}

    sharp_pain_words = ["sharp pain", "shooting pain", "durere ascuțită", "durere care înjunghie"]
    if pain_notes and any(w in pain_notes.lower() for w in sharp_pain_words):
        return {"action": "rest_day", "safety_flag": False,
                "reason_en": "Sharp/shooting pain is a sign to stop and rest that area, not push through it. Consider a doctor or physio if it persists.",
                "reason_ro": "Durerea ascuțită/care înjunghie e un semn să oprești și să odihnești acea zonă, nu să continui. Ia în calcul un medic sau fizioterapeut dacă persistă."}

    # composite readiness score, roughly -2..+2 (higher is better)
    score = (energy - 3) + (sleep_quality - 3) - (soreness - 3) - (stress - 3)
    score = score / 4

    time_limited = available_minutes and available_minutes < planned_minutes * 0.6

    if score <= -1.5:
        action = "rest_day"
        reason_en = "Energy, sleep, soreness and stress are all pointing the same direction today — a full rest or active recovery day is probably the smarter call."
        reason_ro = "Energia, somnul, durerea musculară și stresul arată toate în aceeași direcție azi — o zi de odihnă completă sau recuperare activă e probabil alegerea mai înțeleaptă."
    elif score <= -0.5:
        action = "lighter_workout"
        reason_en = "You're a bit under par today — consider a lighter session: same movements, less weight or fewer sets."
        reason_ro = "Ești puțin sub formă azi — ia în calcul o sesiune mai ușoară: aceleași mișcări, greutate mai mică sau mai puține seturi."
    elif time_limited:
        action = "reduce_sets"
        reason_en = f"Only ~{available_minutes} min available — trim a set or two off each exercise to fit the time you have."
        reason_ro = f"Doar ~{available_minutes} min disponibile — redu una-două serii la fiecare exercițiu ca să te încadrezi în timp."
    else:
        action = "as_planned"
        reason_en = "You're reading as ready to go — stick with today's planned workout."
        reason_ro = "Pari pregătit — rămâi la antrenamentul planificat pentru azi."

    return {"action": action, "safety_flag": False, "reason_en": reason_en, "reason_ro": reason_ro}
