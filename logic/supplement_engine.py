"""
supplement_engine.py
---------------------
A short, conservative, evidence-based supplement stack for a lean-out
phase that's meant to preserve strength. Nothing exotic, nothing with
weak evidence, no "fat burner" pills.

This is general wellness information, NOT medical advice. The app
should always show the disclaimer alongside this list (see templates).
"""


def get_recommendations(profile):
    weight = float(profile.get("weight_kg", 80))
    return [
        {
            "en": "Creatine monohydrate", "ro": "Creatină monohidrat",
            "dose": "5 g / day, every day (no loading phase needed)",
            "why_en": "Best-studied supplement for strength & power; helps offset "
                      "strength loss while in a calorie deficit.",
            "why_ro": "Cel mai studiat supliment pentru forță & putere; ajută la "
                      "menținerea forței în timpul unui deficit caloric.",
        },
        {
            "en": "Whey (or any) protein powder", "ro": "Proteină whey (sau orice tip)",
            "dose": f"Use only to close the gap to your protein target "
                    f"(~{round(2.2*weight)} g/day) if food alone falls short.",
            "why_en": "Convenient way to hit high protein needs during a cut.",
            "why_ro": "Mod convenabil de a atinge necesarul mare de proteine în cură.",
        },
        {
            "en": "Vitamin D3", "ro": "Vitamina D3",
            "dose": "2000-4000 IU/day, especially Oct-Apr (low sun in Romania)",
            "why_en": "Common deficiency at this latitude in autumn/winter; "
                      "supports bone health, immune function, and hormones.",
            "why_ro": "Deficit frecvent la această latitudine toamna/iarna; susține "
                      "sănătatea oaselor, imunitatea și hormonii.",
        },
        {
            "en": "Omega-3 (fish oil)", "ro": "Omega-3 (ulei de pește)",
            "dose": "1-2 g combined EPA+DHA/day, with a meal",
            "why_en": "Supports joint health and recovery, useful if fish intake is low.",
            "why_ro": "Susține sănătatea articulațiilor și recuperarea, util dacă nu "
                      "mănânci pește des.",
        },
        {
            "en": "Magnesium", "ro": "Magneziu",
            "dose": "200-400 mg in the evening",
            "why_en": "Supports sleep quality and recovery; many people fall short "
                      "on magnesium from diet alone.",
            "why_ro": "Susține calitatea somnului și recuperarea; multă lume nu "
                      "atinge necesarul doar din alimentație.",
        },
        {
            "en": "Caffeine (optional)", "ro": "Cofeină (opțional)",
            "dose": "100-200 mg, 30-45 min pre-workout, none after ~4pm",
            "why_en": "Reliable performance boost for strength training if tolerated well.",
            "why_ro": "Îmbunătățește performanța la antrenamentele de forță, dacă e "
                      "tolerată bine.",
        },
    ]


DISCLAIMER_EN = ("This is general information, not medical advice. Check with a "
                  "doctor before starting new supplements, especially if you take "
                  "any medication.")
DISCLAIMER_RO = ("Aceasta este informație generală, nu sfat medical. Discută cu un "
                  "medic înainte de a începe suplimente noi, mai ales dacă iei alte "
                  "medicamente.")
