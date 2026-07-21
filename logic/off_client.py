"""
off_client.py
-------------
Client for the free, open, no-API-key Open Food Facts database
(https://world.openfoodfacts.org) — this is what powers the barcode
scanner's product lookup. Coverage of Romanian supermarket products
(including Lidl Romania) is decent but community-maintained, so it won't
have literally everything; the scanner UI always offers manual entry as a
fallback (see routes/meals.py `scan_manual`).

Design note: the network call (`fetch_product`) is separated from the
parsing (`parse_off_response`) so the parsing logic can be unit-tested
with a saved sample response, without needing a live network connection.

This module NEVER invents nutrition numbers. If a field is missing from
the API response, it comes back as None and `data_complete` is False —
the UI must then show "estimated / please confirm" rather than a made-up
number (this directly implements the app spec's "must not invent
nutritional data" rule).
"""

import json
import urllib.request
import urllib.error

OFF_BASE_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
REQUIRED_FIELDS = ["product_name", "brands", "nutriments", "quantity"]
TIMEOUT_SECONDS = 8


def parse_off_response(data, barcode=None):
    """data: the parsed JSON dict from the OFF API. Returns a normalized,
    None-safe product dict. Pure function — no network I/O — so it's
    directly unit-testable."""
    if not data or data.get("status") != 1 or "product" not in data:
        return {"found": False, "barcode": barcode}

    p = data["product"]
    n = p.get("nutriments", {}) or {}

    def g(*keys):
        for k in keys:
            if k in n and n[k] not in (None, ""):
                try:
                    return round(float(n[k]), 1)
                except (TypeError, ValueError):
                    continue
        return None

    kcal_100g = g("energy-kcal_100g", "energy-kcal")
    protein_100g = g("proteins_100g")
    carb_100g = g("carbohydrates_100g")
    sugar_100g = g("sugars_100g")
    fat_100g = g("fat_100g")
    sat_fat_100g = g("saturated-fat_100g")
    fiber_100g = g("fiber_100g")
    salt_100g = g("salt_100g")

    core_fields = [kcal_100g, protein_100g, carb_100g, fat_100g]
    data_complete = all(v is not None for v in core_fields)

    serving_size_g = None
    serving_raw = p.get("serving_size", "")
    if serving_raw:
        digits = "".join(c for c in serving_raw if c.isdigit() or c == ".")
        try:
            serving_size_g = float(digits) if digits else None
        except ValueError:
            serving_size_g = None

    return {
        "found": True,
        "barcode": barcode or p.get("code"),
        "product_name": p.get("product_name") or p.get("product_name_en") or "Unknown product",
        "brand": p.get("brands", "").split(",")[0].strip() if p.get("brands") else None,
        "package_size": p.get("quantity") or None,
        "serving_size_raw": serving_raw or None,
        "serving_size_g": serving_size_g,
        "per_100g": {
            "kcal": kcal_100g, "protein_g": protein_100g, "carb_g": carb_100g,
            "sugar_g": sugar_100g, "fat_g": fat_100g, "saturated_fat_g": sat_fat_100g,
            "fiber_g": fiber_100g, "salt_g": salt_100g,
        },
        "ingredients_text": p.get("ingredients_text") or p.get("ingredients_text_en") or None,
        "allergens": [a.replace("en:", "").replace("_", " ") for a in (p.get("allergens_tags") or [])],
        "additives": [a.replace("en:", "") for a in (p.get("additives_tags") or [])],
        "image_url": p.get("image_front_small_url") or p.get("image_url"),
        "data_complete": data_complete,
    }


def fetch_product(barcode):
    """Live network call to Open Food Facts. Returns the same shape as
    parse_off_response(). On any network error, returns
    {"found": False, "error": "..."} rather than raising, so routes can
    show a friendly "couldn't reach the product database" message and
    fall back to manual entry."""
    url = OFF_BASE_URL.format(barcode=barcode)
    fields = "product_name,brands,quantity,serving_size,nutriments,ingredients_text,allergens_tags,additives_tags,image_front_small_url,code"
    req = urllib.request.Request(
        f"{url}?fields={fields}",
        headers={"User-Agent": "Exodus-FitnessApp/1.0 (personal free-tier app)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return parse_off_response(data, barcode=barcode)
    except urllib.error.URLError as e:
        return {"found": False, "barcode": barcode, "error": str(e)}
    except (json.JSONDecodeError, TimeoutError) as e:
        return {"found": False, "barcode": barcode, "error": str(e)}


def scale_to_portion(per_100g, portion_g):
    """Scale per-100g nutriment values to an arbitrary portion size in
    grams. Any None input stays None (never fabricate a number)."""
    factor = portion_g / 100.0
    return {k: (round(v * factor, 1) if v is not None else None) for k, v in per_100g.items()}


def goal_fit(product, goal, remaining_kcal=None, lang="en"):
    """Rule-based, explainable 'does this fit my goal' assessment.
    Never claims certainty about data OFF doesn't have."""
    per100 = product.get("per_100g", {})
    kcal, protein, sugar, fiber = per100.get("kcal"), per100.get("protein_g"), per100.get("sugar_g"), per100.get("fiber_g")

    notes_en, notes_ro = [], []
    fit = "neutral"

    if not product.get("data_complete"):
        notes_en.append("Some nutrition values are missing from the database for this product — treat numbers as incomplete and check the label.")
        notes_ro.append("Unele valori nutriționale lipsesc din baza de date pentru acest produs — tratează cifrele ca incomplete și verifică eticheta.")

    if kcal is not None and protein is not None and kcal > 0:
        protein_per_100kcal = protein / (kcal / 100)
        if protein_per_100kcal >= 8:
            notes_en.append("Good protein density relative to its calories.")
            notes_ro.append("Densitate bună de proteine raportat la calorii.")
            fit = "good" if fit == "neutral" else fit
        elif goal == "lean_maintain_strength" and kcal >= 300 and protein_per_100kcal < 4:
            notes_en.append("Calorie-dense with relatively little protein — easy to overeat on a cut, measure your portion.")
            notes_ro.append("Densitate calorică mare cu proteine relativ puține — ușor de mâncat în exces la o cură, măsoară porția.")
            fit = "caution"

    if sugar is not None and sugar >= 15:
        notes_en.append(f"High in sugar ({sugar}g/100g).")
        notes_ro.append(f"Bogat în zahăr ({sugar}g/100g).")
        fit = "caution" if fit != "caution" else fit

    if fiber is not None and fiber >= 5:
        notes_en.append("Good fiber content.")
        notes_ro.append("Conținut bun de fibre.")

    if goal == "muscle_gain" and kcal is not None and kcal < 150 and (protein or 0) < 5:
        notes_en.append("Low in both calories and protein — fine as a light snack, won't do much for a bulk on its own.")
        notes_ro.append("Slab în calorii și proteine — bun ca gustare ușoară, dar nu ajută mult la un bulk de unul singur.")

    return {"fit": fit, "notes_en": notes_en, "notes_ro": notes_ro}
