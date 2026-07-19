"""
i18n.py
-------
Tiny bilingual (English / Romanian) text dictionary for Exodus.

How it works
------------
TRANSLATIONS is a dict of dicts: TRANSLATIONS[lang][key] -> string.
`t(key, lang)` looks up a key for the given language and falls back to
English (then to the raw key) if something is missing, so the app never
crashes just because a translation wasn't added yet.

Where to add new text
----------------------
Add a new key to BOTH the "en" and "ro" blocks below, then call
`t("your_key", lang)` from a route or template.
"""

TRANSLATIONS = {
    "en": {
        "app_name": "Exodus",
        "tagline": "Your personal strength & recomposition coach",
        "nav_dashboard": "Dashboard",
        "nav_workout": "Workout",
        "nav_meals": "Meals",
        "nav_progress": "Progress",
        "nav_settings": "Settings",
        "today_is": "Today is",
        "training_day": "Training day",
        "rest_day": "Rest day",
        "todays_workout": "Today's workout",
        "no_workout_today": "No lifting today — recovery day. Walk, stretch, sleep well.",
        "calories_target": "Calorie target",
        "protein_target": "Protein target",
        "carbs_target": "Carbs",
        "fat_target": "Fat",
        "coach_says": "Coach notes",
        "log_weight": "Log body weight",
        "log_workout": "Log today's sets",
        "current_phase": "Current phase",
        "phase_ramp": "Return-to-training ramp (week {week} of 3)",
        "phase_normal": "Normal progression",
        "sets": "Sets",
        "reps": "Reps",
        "target_weight": "Target weight",
        "exercise": "Exercise",
        "save": "Save",
        "supplements": "Supplements",
        "meal_ideas": "Meal ideas",
        "weight_history": "Body weight history",
        "settings_title": "Settings & profile",
        "language": "Language",
        "goal": "Goal",
        "height": "Height (cm)",
        "weight": "Weight (kg)",
        "prs": "Personal records (kg)",
        "training_days": "Training days / week",
        "saved": "Saved.",
    },
    "ro": {
        "app_name": "Exodus",
        "tagline": "Antrenorul tău personal de forță și recompoziție corporală",
        "nav_dashboard": "Panou",
        "nav_workout": "Antrenament",
        "nav_meals": "Mese",
        "nav_progress": "Progres",
        "nav_settings": "Setări",
        "today_is": "Astăzi este",
        "training_day": "Zi de antrenament",
        "rest_day": "Zi de odihnă",
        "todays_workout": "Antrenamentul de azi",
        "no_workout_today": "Fără antrenament azi — zi de recuperare. Mișcare ușoară, stretching, somn bun.",
        "calories_target": "Calorii țintă",
        "protein_target": "Proteine țintă",
        "carbs_target": "Carbohidrați",
        "fat_target": "Grăsimi",
        "coach_says": "Notele antrenorului",
        "log_weight": "Înregistrează greutatea",
        "log_workout": "Înregistrează seriile de azi",
        "current_phase": "Faza curentă",
        "phase_ramp": "Revenire la antrenament (săptămâna {week} din 3)",
        "phase_normal": "Progresie normală",
        "sets": "Serii",
        "reps": "Repetări",
        "target_weight": "Greutate țintă",
        "exercise": "Exercițiu",
        "save": "Salvează",
        "supplements": "Suplimente",
        "meal_ideas": "Idei de mese",
        "weight_history": "Istoric greutate corporală",
        "settings_title": "Setări & profil",
        "language": "Limbă",
        "goal": "Obiectiv",
        "height": "Înălțime (cm)",
        "weight": "Greutate (kg)",
        "prs": "Recorduri personale (kg)",
        "training_days": "Zile de antrenament / săptămână",
        "saved": "Salvat.",
    },
}


def t(key, lang="en"):
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    if key in lang_dict:
        return lang_dict[key]
    return TRANSLATIONS["en"].get(key, key)
