"""
assistant_engine.py
--------------------
The "AI Assistant" — per the earlier scoping decision, this is a
rule-based intent router, not an LLM: it keyword-matches the user's
message (EN or RO) to one of a fixed set of intents, then calls the same
engines the rest of the app uses (nutrition/workout/crossfit/safety) to
build a real, data-backed answer. Free forever, fully explainable, and
directly reuses logic that's already tested elsewhere.

It is NOT a general chatbot — messages that don't match a known intent get
a fallback response listing what it *can* help with. That's an honest
limitation of the rule-based approach the user chose over a paid LLM.

Every response passes through logic.safety.check_red_flags first.
"""

import re

from logic.safety import check_red_flags, SAFETY_MESSAGE_EN, SAFETY_MESSAGE_RO
from logic.nutrition_engine import (
    suggest_meals_for_remaining, filter_meals, daily_totals, recently_eaten_meal_keys,
)
from logic.workout_engine import suggest_replacements, replacement_explanation, get_phase
from logic.crossfit_engine import generate_workout
from logic.safety import suggest_readiness_action

QUICK_QUESTIONS = [
    {"en": "What should I eat today?", "ro": "Ce ar trebui să mănânc azi?", "intent": "what_to_eat"},
    {"en": "How many calories do I have left?", "ro": "Câte calorii mai am rămase?", "intent": "calories_left"},
    {"en": "Should I train today if I'm sore?", "ro": "Ar trebui să mă antrenez azi dacă sunt dureri?", "intent": "sore_train"},
    {"en": "Create a 30-minute workout for me.", "ro": "Creează-mi un antrenament de 30 de minute.", "intent": "quick_workout"},
    {"en": "Create a high-protein Romanian meal.", "ro": "Creează o masă românească bogată în proteine.", "intent": "romanian_high_protein"},
    {"en": "Why am I not progressing?", "ro": "De ce nu mai progresez?", "intent": "not_progressing"},
]


# colloquial/plural terms people actually type, mapped to a specific exercise key.
# Checked before the looser full-name match below.
EXERCISE_ALIASES = {
    "squats": "back_squat", "squat": "back_squat", "squatting": "back_squat",
    "bench": "bench_press", "benching": "bench_press", "bench press": "bench_press",
    "deadlifts": "deadlift", "deadlifting": "deadlift",
    "pullups": "pullup", "pull-ups": "pullup", "pull ups": "pullup",
    "chinups": "chinup", "chin-ups": "chinup",
    "ohp": "overhead_press", "shoulder press": "overhead_press",
    "curls": "barbell_curl", "bicep curls": "barbell_curl",
    "rows": "barbell_row", "rowing": "barbell_row",
    "genuflexiuni": "back_squat", "îndreptări": "deadlift", "tracțiuni": "pullup",
}


def _extract_exercise_from_text(text, exercises):
    text_l = text.lower()
    for alias, key in EXERCISE_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text_l):
            match = next((e for e in exercises if e["key"] == key), None)
            if match:
                return match
    for ex in exercises:
        if ex["name_en"].lower() in text_l or ex["name_ro"].lower() in text_l or ex["key"].replace("_", " ") in text_l:
            return ex
    return None


def _match_intent(text):
    t = text.lower()
    rules = [
        ("what_to_eat", [r"what should i eat", r"what to eat", r"ce (ar trebui )?să mănânc", r"ce mănânc"]),
        ("cook_with", [r"cook with", r"what can i (make|cook)", r"ce pot găti", r"ce pot face cu"]),
        ("calories_left", [r"calories.*left", r"how many calories", r"câte calorii", r"calorii.*rămas"]),
        ("replace_exercise", [r"replace (this |the )?exercise", r"alternative to", r"înlocui", r"alternativă la"]),
        ("not_progressing", [r"not progress", r"why am i not", r"nu (mai )?progresez", r"stagnat"]),
        ("sore_train", [r"train.*sore", r"sore.*train", r"antrenez.*dureri", r"dureri.*antrenez"]),
        ("adjust_slept_badly", [r"slept badly", r"bad sleep", r"dormit prost", r"somn prost"]),
        ("shopping_lidl", [r"buy from lidl", r"cumpăr.*lidl", r"lidl"]),
        ("quick_workout", [r"\d+[\s-]*minute workout", r"create a workout", r"antrenament de \d+", r"creează.*antrenament"]),
        ("romanian_high_protein", [r"romanian.*meal", r"masă românească", r"mâncare românească"]),
    ]
    for intent, patterns in rules:
        if any(re.search(p, t) for p in patterns):
            return intent
    return None


def answer(message, lang, profile_dict, targets, meal_log_today, all_meals, all_exercises,
           workout_set_logs=None):
    if check_red_flags(message):
        return {"intent": "safety", "text": SAFETY_MESSAGE_RO if lang == "ro" else SAFETY_MESSAGE_EN}

    intent = _match_intent(message)
    is_ro = lang == "ro"

    if intent == "what_to_eat":
        totals = daily_totals(meal_log_today)
        remaining_kcal = max(targets["target_calories"] - totals["kcal"], 0)
        remaining_protein = max(targets["protein_g"] - totals["protein_g"], 0)
        recent = recently_eaten_meal_keys(meal_log_today, days=5)
        suggestions = suggest_meals_for_remaining(all_meals, remaining_kcal, remaining_protein,
                                                    recently_used_keys=recent, limit=3)
        if not suggestions:
            text = ("You're already close to today's targets — light snack territory only." if not is_ro
                    else "Ești deja aproape de țintele de azi — doar loc pentru o gustare ușoară.")
        else:
            names = ", ".join(s["name_ro" if is_ro else "name_en"] for s in suggestions)
            text = (f"You have ~{round(remaining_kcal)} kcal and ~{round(remaining_protein)}g protein left today. "
                    f"Try: {names}." if not is_ro else
                    f"Mai ai ~{round(remaining_kcal)} kcal și ~{round(remaining_protein)}g proteine azi. "
                    f"Încearcă: {names}.")
        return {"intent": intent, "text": text, "meals": suggestions}

    if intent == "cook_with":
        # naive ingredient extraction: match any food-ish words against meal ingredient names
        words = set(re.findall(r"[a-zăâîșț]+", message.lower()))
        candidates = []
        for m in all_meals:
            ing_names = {i["name_en"].lower() for i in m["ingredients"]} | {i["name_ro"].lower() for i in m["ingredients"]}
            if any(w in " ".join(ing_names) for w in words if len(w) > 3):
                candidates.append(m)
        candidates = candidates[:3]
        if candidates:
            names = ", ".join(m["name_ro" if is_ro else "name_en"] for m in candidates)
            text = (f"With what you mentioned, you could make: {names}." if not is_ro
                    else f"Cu ce ai menționat, ai putea face: {names}.")
        else:
            text = ("Couldn't match those ingredients to a saved recipe — try the Meals tab filters instead." if not is_ro
                    else "Nu am putut potrivi acele ingrediente cu o rețetă salvată — încearcă filtrele din tab-ul Mese.")
        return {"intent": intent, "text": text, "meals": candidates}

    if intent == "calories_left":
        totals = daily_totals(meal_log_today)
        remaining = max(targets["target_calories"] - totals["kcal"], 0)
        text = (f"You've logged {totals['kcal']} kcal today, target is {targets['target_calories']} — "
                f"about {remaining} kcal left." if not is_ro else
                f"Ai înregistrat {totals['kcal']} kcal azi, ținta e {targets['target_calories']} — "
                f"mai ai aproximativ {remaining} kcal.")
        return {"intent": intent, "text": text}

    if intent == "replace_exercise":
        ex = _extract_exercise_from_text(message, all_exercises)
        if not ex:
            text = ("Tell me which exercise (e.g. 'alternative to squats') and I'll suggest a swap." if not is_ro
                    else "Spune-mi ce exercițiu (ex. 'alternativă la genuflexiuni') și îți sugerez un înlocuitor.")
            return {"intent": intent, "text": text}
        repl = suggest_replacements(all_exercises, ex["key"], profile_dict)
        if not repl["recommended"]:
            text = ("Couldn't find a good equipment-matched swap — check the Workouts tab's full replace list." if not is_ro
                    else "Nu am găsit un înlocuitor potrivit cu echipamentul tău — verifică lista completă din tab-ul Antrenamente.")
        else:
            top = repl["recommended"][0]
            expl = replacement_explanation(ex, top, lang)
            name = top["name_ro" if is_ro else "name_en"]
            text = (f"Try {name} instead. {expl}" if not is_ro else f"Încearcă {name} în loc. {expl}")
        return {"intent": intent, "text": text, "replacements": repl["recommended"]}

    if intent == "not_progressing":
        ex = _extract_exercise_from_text(message, all_exercises)
        text = (("Common causes of a stall: not enough recovery (sleep/protein/calories), "
                  "the jump between sessions is too big, or it's just been a couple of tough weeks — "
                  "check your Progress tab for the trend before changing anything.")
                 if not is_ro else
                 ("Cauze frecvente ale unui blocaj: recuperare insuficientă (somn/proteine/calorii), "
                  "saltul între sesiuni e prea mare, sau au fost pur și simplu câteva săptămâni grele — "
                  "verifică tab-ul Progres pentru tendință înainte să schimbi ceva."))
        if ex:
            name = ex["name_ro" if is_ro else "name_en"]
            text = (f"On {name} specifically: " if not is_ro else f"Specific la {name}: ") + text
        return {"intent": intent, "text": text}

    if intent in ("sore_train", "adjust_slept_badly"):
        # crude parse of a 1-5 scale from the message isn't reliable via keywords alone —
        # point the user to the full readiness check-in for an accurate answer.
        text = ("Use the Readiness Check-in before today's workout (Workouts tab) for a real "
                "answer based on your energy/sleep/soreness/stress — it'll suggest keeping the "
                "plan, going lighter, or resting." if not is_ro else
                "Folosește Verificarea de pregătire înainte de antrenamentul de azi (tab-ul "
                "Antrenamente) pentru un răspuns real bazat pe energie/somn/dureri/stres — îți va "
                "sugera să păstrezi planul, să mergi mai ușor, sau să te odihnești.")
        return {"intent": intent, "text": text, "goto": "readiness_checkin"}

    if intent == "shopping_lidl":
        text = ("I can't browse live Lidl inventory or prices, but you can scan any product's "
                "barcode in the Scanner tab and I'll tell you how it fits your goal, or check your "
                "Shopping List (built from your saved meals) before you go." if not is_ro else
                "Nu pot naviga stocul sau prețurile live de la Lidl, dar poți scana codul de bare al "
                "oricărui produs în tab-ul Scanner și îți spun cum se potrivește cu obiectivul tău, "
                "sau verifică Lista de cumpărături (construită din mesele salvate) înainte să mergi.")
        return {"intent": intent, "text": text, "goto": "shopping_list"}

    if intent == "quick_workout":
        minutes_match = re.search(r"(\d+)[\s-]*min", message.lower())
        duration = int(minutes_match.group(1)) if minutes_match else 30
        wod = generate_workout(all_exercises, profile_dict, wtype="AMRAP", duration_min=duration)
        names = ", ".join(m["exercise_key"].replace("_", " ") for m in wod["movements"])
        text = (f"Here's a {duration}-min AMRAP: {names}. Full details on the CrossFit tab." if not is_ro
                else f"Iată un AMRAP de {duration} min: {names}. Detalii complete în tab-ul CrossFit.")
        return {"intent": intent, "text": text, "workout": wod}

    if intent == "romanian_high_protein":
        candidates = filter_meals(all_meals, tags=["romanian", "high_protein"]) or \
                     filter_meals(all_meals, tags=["romanian"])
        if candidates:
            m = candidates[0]
            name = m["name_ro" if is_ro else "name_en"]
            text = (f"Try {name} — {m['protein_g_per_serving']}g protein, {m['kcal_per_serving']} kcal per serving."
                    if not is_ro else
                    f"Încearcă {name} — {m['protein_g_per_serving']}g proteine, {m['kcal_per_serving']} kcal per porție.")
        else:
            text = ("No Romanian high-protein meal saved yet — add one from the Meals tab." if not is_ro
                    else "Nu există încă o masă românească bogată în proteine salvată — adaugă una din tab-ul Mese.")
        return {"intent": intent, "text": text, "meals": candidates[:1]}

    # fallback
    text = (
        "I can help with: what to eat today, calories/macros left, exercise swaps, why a lift "
        "stalled, readiness before training, quick workout generation, and meal ideas. Try one of "
        "the quick questions below." if not is_ro else
        "Te pot ajuta cu: ce să mănânci azi, calorii/macronutrienți rămași, înlocuiri de exerciții, "
        "de ce a stagnat o mișcare, pregătirea înainte de antrenament, generarea rapidă de "
        "antrenamente și idei de mese. Încearcă una din întrebările rapide de mai jos."
    )
    return {"intent": "fallback", "text": text}
