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
        "today_so_far": "Today so far",
        "log_food": "Log food",
        "food": "Food",
        "quantity": "Quantity",
        "meal_type": "Meal",
        "add": "Add",
        "todays_food_log": "Today's food log",
        "no_food_logged": "Nothing logged yet today.",
        "delete": "Remove",
        "calorie_history": "Calorie history (14 days)",
        "breakfast": "Breakfast",
        "lunch": "Lunch",
        "dinner": "Dinner",
        "snack": "Snack",
        "of_target": "of target",
        "this_weeks_accessories": "Rotates weekly",

        # --- auth ---
        "email": "Email", "password": "Password", "confirm_password": "Confirm password",
        "new_password": "New password", "log_in": "Log in", "create_account": "Create account",
        "already_have_account": "Already have an account? Log in",
        "forgot_password": "Forgot password?", "back_to_login": "Back to login",
        "send_reset_link": "Send reset link", "reset_password": "Reset password",
        "smtp_not_configured_hint": "Email isn't configured on this server yet, so here's your reset link directly:",
        "logout": "Log out", "your_data": "Your data", "export_data": "Export my data (JSON)",
        "delete_account": "Delete account",

        # --- onboarding ---
        "step": "Step", "continue": "Continue", "finish": "Finish", "optional": "optional",
        "onboarding_basics_title": "The basics", "onboarding_goal_title": "Goal & training",
        "onboarding_diet_title": "Diet & preferences", "onboarding_health_title": "Health & recovery",
        "name_nickname": "Name / nickname", "age": "Age", "sex": "Sex",
        "male": "Male", "female": "Female", "prefer_not_say": "Prefer not to say",
        "target_weight": "Target weight (kg)", "units": "Units",
        "experience_level": "Training experience", "beginner": "Beginner", "intermediate": "Intermediate",
        "advanced": "Advanced", "activity_level": "Activity level", "sedentary": "Sedentary",
        "moderate": "Moderate", "high": "High", "preferred_style": "Preferred training style",
        "equipment_available": "Equipment available", "dietary_preferences": "Dietary preferences",
        "allergies": "Allergies", "dislikes": "Disliked foods", "comma_separated": "comma-separated",
        "meal_frequency": "Meals per day", "injuries_notes": "Injuries / limitations (notes)",
        "injury_areas": "Injury areas (used to avoid unsafe exercises)", "sleep_hours": "Average sleep (hours)",
        "step_target": "Daily step target", "bench": "Bench", "squat": "Squat", "deadlift": "Deadlift",
        "pullups": "Pull-ups (clean reps)",

        # --- goals ---
        "goal_lean": "Fat Loss + Keep Strength", "goal_maintenance": "Maintenance", "goal_gain": "Muscle Gain",
        "goal_transitioning_hint": "Calories are ramping gradually toward your new goal — see Settings for details.",

        # --- meals / scanner / shopping ---
        "estimated": "estimated", "regenerate_day": "Suggest a full day", "servings": "Servings",
        "total": "total", "per_serving": "per serving", "ingredients": "Ingredients",
        "raw_weight_note": "raw/as-purchased weight unless noted", "instructions": "Instructions",
        "substitutions": "Substitutions", "toggle_favorite": "Favorite", "add_to_shopping_list": "Add to shopping list",
        "rate_this_meal": "Rate this meal", "view": "View", "clear_filters": "Clear filters",
        "nav_scanner": "Scanner", "nav_shopping": "Shopping", "scanner_hint": "Scan a barcode or search manually — nothing is invented if data is missing.",
        "start_camera": "Start camera", "or_enter_barcode": "or enter barcode", "lookup": "Look up",
        "portion_grams": "Portion (g)", "log_this_product": "Log this product", "manual_search": "Manual search",
        "search_food": "Search food", "item_name": "Item name", "have_at_home": "have at home",
        "shopping_list_empty": "Your shopping list is empty.",

        # --- workouts ---
        "no_active_plan": "You don't have an active plan yet.", "generate_plan": "Generate a plan",
        "your_weekly_plan": "Your weekly plan", "generate_new_plan": "Generate a new plan",
        "main_lift": "main lift", "last_time": "last time", "replace_exercise": "Replace exercise",
        "notes": "Notes", "felt_pain": "I felt pain", "log_set": "Log set", "edit": "Edit",
        "add_exercise": "Add exercise", "exercise_key_hint": "exercise key, e.g. bench_press",
        "browse_exercise_library": "Browse the exercise library for keys →", "rest_seconds": "Rest (sec)",
        "currently": "Currently", "recommended": "Recommended", "same_muscle": "Same primary muscle",
        "same_pattern": "Same movement pattern", "use_this": "Use this", "all": "All",
        "nav_exercise_library": "Exercise Library", "primary_muscle": "Primary muscle",
        "secondary_muscles": "Secondary muscles", "equipment_needed": "Equipment needed",
        "breathing": "Breathing", "common_mistakes": "Common mistakes", "safety_tips": "Safety tips",
        "easier": "Easier", "harder": "Harder", "search_video_demo": "Search for a video demo on YouTube",
        "video_disclaimer": "external results, not curated or verified by this app",
        "nav_readiness": "Readiness", "energy_level": "Energy level", "sleep_quality": "Sleep quality",
        "soreness": "Muscle soreness", "stress_level": "Stress level", "available_minutes": "Time available (min)",
        "pain_notes": "Any pain or discomfort?", "check_in": "Check in", "suggestion": "Suggestion",
        "you_decide": "You always make the final call — this is just a suggestion.",
        "as_planned": "Train as planned", "reduce_weight": "Reduce weight", "reduce_sets": "Reduce sets",
        "lighter_workout": "Lighter workout", "movements": "Movements",

        # --- crossfit ---
        "nav_crossfit": "CrossFit", "generate_workout": "Generate a workout", "generate": "Generate",
        "scaling_notes": "Scaling notes", "technique_notes": "Technique notes",
        "score_placeholder": "e.g. 14:32 or 8 rounds + 5 reps", "log_score": "Log score",

        # --- progress ---
        "week": "Week", "month": "Month", "3months": "3 Months", "6months": "6 Months", "year": "Year",
        "weekly_summary": "Weekly summary", "no_data_yet": "Not enough data yet — log a few sessions/meals first.",
        "strength_progress": "Strength progress", "training_volume": "Training volume",
        "consistency": "Consistency", "protein_target_hit_days": "Days protein target was hit",
        "recent_prs": "Recent personal records", "weekly_progress": "This week's training",
        "sessions_this_week": "sessions this week", "weight_trend": "Weight trend", "fiber": "Fiber",
        "water": "Water",

        # --- assistant ---
        "nav_assistant": "Assistant", "assistant_disclaimer": "Rule-based, not a general chatbot — answers use your real data, not a language model.",
        "ask_anything": "Ask a question...", "send": "Send", "you_asked": "You asked",
        "assistant_of_the_day": "Ask the assistant", "assistant_dashboard_hint": "Get a quick, data-based answer about meals, workouts, or recovery.",

        # --- misc ---
        "page_not_found": "That page doesn't exist.",
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
        "today_so_far": "Azi până acum",
        "log_food": "Înregistrează o masă",
        "food": "Aliment",
        "quantity": "Cantitate",
        "meal_type": "Masă",
        "add": "Adaugă",
        "todays_food_log": "Jurnal alimentar de azi",
        "no_food_logged": "Nimic înregistrat azi încă.",
        "delete": "Șterge",
        "calorie_history": "Istoric calorii (14 zile)",
        "breakfast": "Mic dejun",
        "lunch": "Prânz",
        "dinner": "Cină",
        "snack": "Gustare",
        "of_target": "din țintă",
        "this_weeks_accessories": "Se rotesc săptămânal",

        # --- auth ---
        "email": "Email", "password": "Parolă", "confirm_password": "Confirmă parola",
        "new_password": "Parolă nouă", "log_in": "Autentificare", "create_account": "Creează cont",
        "already_have_account": "Ai deja cont? Autentifică-te",
        "forgot_password": "Ai uitat parola?", "back_to_login": "Înapoi la autentificare",
        "send_reset_link": "Trimite link de resetare", "reset_password": "Resetează parola",
        "smtp_not_configured_hint": "Email-ul nu e configurat încă pe acest server, așa că iată linkul de resetare direct:",
        "logout": "Deconectare", "your_data": "Datele tale", "export_data": "Exportă datele mele (JSON)",
        "delete_account": "Șterge contul",

        # --- onboarding ---
        "step": "Pas", "continue": "Continuă", "finish": "Finalizează", "optional": "opțional",
        "onboarding_basics_title": "Informații de bază", "onboarding_goal_title": "Obiectiv & antrenament",
        "onboarding_diet_title": "Dietă & preferințe", "onboarding_health_title": "Sănătate & recuperare",
        "name_nickname": "Nume / poreclă", "age": "Vârstă", "sex": "Sex",
        "male": "Masculin", "female": "Feminin", "prefer_not_say": "Prefer să nu spun",
        "target_weight": "Greutate țintă (kg)", "units": "Unități de măsură",
        "experience_level": "Experiență de antrenament", "beginner": "Începător", "intermediate": "Intermediar",
        "advanced": "Avansat", "activity_level": "Nivel de activitate", "sedentary": "Sedentar",
        "moderate": "Moderat", "high": "Ridicat", "preferred_style": "Stil de antrenament preferat",
        "equipment_available": "Echipament disponibil", "dietary_preferences": "Preferințe alimentare",
        "allergies": "Alergii", "dislikes": "Alimente care nu-ți plac", "comma_separated": "separate prin virgulă",
        "meal_frequency": "Mese pe zi", "injuries_notes": "Accidentări / limitări (note)",
        "injury_areas": "Zone accidentate (folosite pentru a evita exerciții nesigure)", "sleep_hours": "Somn mediu (ore)",
        "step_target": "Țintă pași zilnici", "bench": "Împins culcat", "squat": "Genuflexiune", "deadlift": "Îndreptări",
        "pullups": "Tracțiuni (repetări curate)",

        # --- goals ---
        "goal_lean": "Slăbire + Păstrarea Forței", "goal_maintenance": "Menținere", "goal_gain": "Creștere Musculară",
        "goal_transitioning_hint": "Caloriile cresc/scad treptat spre noul obiectiv — vezi Setări pentru detalii.",

        # --- meals / scanner / shopping ---
        "estimated": "estimat", "regenerate_day": "Sugerează o zi completă", "servings": "Porții",
        "total": "total", "per_serving": "per porție", "ingredients": "Ingrediente",
        "raw_weight_note": "greutate crudă/cumpărată dacă nu e specificat altfel", "instructions": "Instrucțiuni",
        "substitutions": "Înlocuiri", "toggle_favorite": "Favorit", "add_to_shopping_list": "Adaugă în lista de cumpărături",
        "rate_this_meal": "Evaluează această masă", "view": "Vezi", "clear_filters": "Șterge filtrele",
        "nav_scanner": "Scanner", "nav_shopping": "Cumpărături", "scanner_hint": "Scanează un cod de bare sau caută manual — nimic nu e inventat dacă lipsesc date.",
        "start_camera": "Pornește camera", "or_enter_barcode": "sau introdu codul de bare", "lookup": "Caută",
        "portion_grams": "Porție (g)", "log_this_product": "Înregistrează acest produs", "manual_search": "Căutare manuală",
        "search_food": "Caută aliment", "item_name": "Denumire produs", "have_at_home": "ai deja acasă",
        "shopping_list_empty": "Lista ta de cumpărături e goală.",

        # --- workouts ---
        "no_active_plan": "Nu ai încă un plan activ.", "generate_plan": "Generează un plan",
        "your_weekly_plan": "Planul tău săptămânal", "generate_new_plan": "Generează un plan nou",
        "main_lift": "exercițiu principal", "last_time": "data trecută", "replace_exercise": "Înlocuiește exercițiul",
        "notes": "Note", "felt_pain": "Am simțit durere", "log_set": "Înregistrează seria", "edit": "Editează",
        "add_exercise": "Adaugă exercițiu", "exercise_key_hint": "cheie exercițiu, ex. bench_press",
        "browse_exercise_library": "Vezi biblioteca de exerciții pentru chei →", "rest_seconds": "Odihnă (sec)",
        "currently": "În prezent", "recommended": "Recomandat", "same_muscle": "Același mușchi principal",
        "same_pattern": "Același tipar de mișcare", "use_this": "Folosește acesta", "all": "Toate",
        "nav_exercise_library": "Biblioteca de Exerciții", "primary_muscle": "Mușchi principal",
        "secondary_muscles": "Mușchi secundari", "equipment_needed": "Echipament necesar",
        "breathing": "Respirație", "common_mistakes": "Greșeli frecvente", "safety_tips": "Sfaturi de siguranță",
        "easier": "Mai ușor", "harder": "Mai greu", "search_video_demo": "Caută un videoclip demonstrativ pe YouTube",
        "video_disclaimer": "rezultate externe, neverificate de această aplicație",
        "nav_readiness": "Pregătire", "energy_level": "Nivel de energie", "sleep_quality": "Calitatea somnului",
        "soreness": "Dureri musculare", "stress_level": "Nivel de stres", "available_minutes": "Timp disponibil (min)",
        "pain_notes": "Ai vreo durere sau disconfort?", "check_in": "Verifică-te", "suggestion": "Sugestie",
        "you_decide": "Decizia finală îți aparține mereu — asta e doar o sugestie.",
        "as_planned": "Antrenează-te ca planificat", "reduce_weight": "Redu greutatea", "reduce_sets": "Redu seriile",
        "lighter_workout": "Antrenament mai ușor", "movements": "Mișcări",

        # --- crossfit ---
        "nav_crossfit": "CrossFit", "generate_workout": "Generează un antrenament", "generate": "Generează",
        "scaling_notes": "Note de ajustare", "technique_notes": "Note de tehnică",
        "score_placeholder": "ex. 14:32 sau 8 runde + 5 rep.", "log_score": "Înregistrează scorul",

        # --- progress ---
        "week": "Săptămână", "month": "Lună", "3months": "3 Luni", "6months": "6 Luni", "year": "An",
        "weekly_summary": "Rezumat săptămânal", "no_data_yet": "Încă nu sunt destule date — înregistrează câteva sesiuni/mese mai întâi.",
        "strength_progress": "Progres de forță", "training_volume": "Volum de antrenament",
        "consistency": "Consistență", "protein_target_hit_days": "Zile în care ținta de proteine a fost atinsă",
        "recent_prs": "Recorduri personale recente", "weekly_progress": "Antrenamentul din această săptămână",
        "sessions_this_week": "antrenamente săptămâna asta", "weight_trend": "Tendința greutății", "fiber": "Fibre",
        "water": "Apă",

        # --- assistant ---
        "nav_assistant": "Asistent", "assistant_disclaimer": "Bazat pe reguli, nu un chatbot general — răspunsurile folosesc datele tale reale, nu un model de limbaj.",
        "ask_anything": "Pune o întrebare...", "send": "Trimite", "you_asked": "Ai întrebat",
        "assistant_of_the_day": "Întreabă asistentul", "assistant_dashboard_hint": "Primește un răspuns rapid, bazat pe date, despre mese, antrenamente sau recuperare.",

        # --- misc ---
        "page_not_found": "Această pagină nu există.",
    },
}


def t(key, lang="en"):
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    if key in lang_dict:
        return lang_dict[key]
    return TRANSLATIONS["en"].get(key, key)
