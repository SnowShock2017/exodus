"""
routes/meals.py
----------------
Meals tab (goal buttons, targets, food log, browse/filter/favorite/rate
meal templates, regenerate-day suggestion), the barcode/product Scanner,
and the Shopping List — grouped in one file since they all revolve around
food data.
"""

from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import (
    MealLogEntry, FavoriteMeal, MealRating,
    ShoppingListItem,
)
from logic.helpers import profile_to_dict, meal_log_to_dict
from logic.cache import get_meals, get_foods
from logic.goal_engine import calculate_targets, switch_goal, GOAL_LABELS, GOAL_DESCRIPTIONS
from logic.nutrition_engine import (
    find_food, build_log_entry, daily_totals, progress_pct, MEAL_TYPES, MEAL_TAGS,
    filter_meals, scale_meal, suggest_day_plan, recently_eaten_meal_keys,
    generate_shopping_list,
)
from logic.off_client import fetch_product, scale_to_portion, goal_fit

bp = Blueprint("meals", __name__, url_prefix="/meals")


def _all_meals():
    return get_meals()


def _all_foods():
    return get_foods()


@bp.route("/")
@login_required
def index():
    profile = current_user.profile
    lang = profile.language
    targets = calculate_targets(profile)

    today_entries_rows = MealLogEntry.query.filter_by(user_id=current_user.id, date=date.today().isoformat()).all()
    today_entries = [meal_log_to_dict(e) for e in today_entries_rows]
    totals = daily_totals(today_entries)
    progress = {
        "kcal": progress_pct(totals["kcal"], targets["target_calories"]),
        "protein_g": progress_pct(totals["protein_g"], targets["protein_g"]),
        "carb_g": progress_pct(totals["carb_g"], targets["carb_g"]),
        "fat_g": progress_pct(totals["fat_g"], targets["fat_g"]),
    }

    tag_filter = request.args.getlist("tag")
    max_kcal = request.args.get("max_kcal", type=int)
    min_protein = request.args.get("min_protein", type=int)
    max_prep = request.args.get("max_prep", type=int)

    meals = _all_meals()
    filtered_meals = filter_meals(meals, tags=tag_filter or None, max_kcal=max_kcal,
                                   min_protein=min_protein, max_prep_min=max_prep)

    favorite_keys = {f.meal_key for f in FavoriteMeal.query.filter_by(user_id=current_user.id).all()}
    ratings = {r.meal_key: r.rating for r in MealRating.query.filter_by(user_id=current_user.id).all()}

    food_db = _all_foods()

    return render_template(
        "meals/index.html", profile=profile, targets=targets, totals=totals, progress=progress,
        today_entries=today_entries, meal_types=MEAL_TYPES, food_db=food_db,
        meals=filtered_meals, all_tags=MEAL_TAGS, active_tags=tag_filter,
        favorite_keys=favorite_keys, ratings=ratings,
        goal_labels=GOAL_LABELS, goal_descriptions=GOAL_DESCRIPTIONS,
    )


@bp.route("/goal", methods=["POST"])
@login_required
def set_goal():
    profile = current_user.profile
    new_goal = request.form.get("goal")
    if new_goal and new_goal in GOAL_LABELS:
        explanation = switch_goal(profile, new_goal)
        db.session.commit()
        flash(explanation["ro" if profile.language == "ro" else "en"], "info")
    return redirect(url_for("meals.index"))


@bp.route("/log", methods=["POST"])
@login_required
def log_food():
    profile = current_user.profile
    food_name = request.form.get("food_name")
    qty = request.form.get("qty")
    meal_type = request.form.get("meal_type", "snack")

    food = find_food(_all_foods(), food_name, profile.language)
    if food and qty:
        try:
            qty_val = float(qty)
        except ValueError:
            qty_val = None
        if qty_val and qty_val > 0:
            entry_dict = build_log_entry(food, qty_val, meal_type, profile.language)
            db.session.add(MealLogEntry(user_id=current_user.id, date=date.today().isoformat(), **entry_dict))
            db.session.commit()
    return redirect(url_for("meals.index"))


@bp.route("/delete/<int:entry_id>", methods=["POST"])
@login_required
def delete_food(entry_id):
    entry = MealLogEntry.query.filter_by(id=entry_id, user_id=current_user.id).first()
    if entry:
        db.session.delete(entry)
        db.session.commit()
    return redirect(url_for("meals.index"))


@bp.route("/favorite/<meal_key>", methods=["POST"])
@login_required
def toggle_favorite(meal_key):
    existing = FavoriteMeal.query.filter_by(user_id=current_user.id, meal_key=meal_key).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(FavoriteMeal(user_id=current_user.id, meal_key=meal_key))
    db.session.commit()
    return redirect(request.referrer or url_for("meals.index"))


@bp.route("/rate/<meal_key>", methods=["POST"])
@login_required
def rate_meal(meal_key):
    rating = request.form.get("rating", type=int)
    if rating and 1 <= rating <= 5:
        existing = MealRating.query.filter_by(user_id=current_user.id, meal_key=meal_key).first()
        if existing:
            existing.rating = rating
        else:
            db.session.add(MealRating(user_id=current_user.id, meal_key=meal_key, rating=rating))
        db.session.commit()
    return redirect(request.referrer or url_for("meals.index"))


@bp.route("/meal/<meal_key>")
@login_required
def meal_detail(meal_key):
    profile = current_user.profile
    meal = next((m for m in _all_meals() if m["key"] == meal_key), None)
    if not meal:
        return redirect(url_for("meals.index"))
    servings = request.args.get("servings", type=int, default=meal["base_servings"])
    scaled = scale_meal(meal, servings)
    return render_template("meals/detail.html", profile=profile, meal=meal, scaled=scaled, servings=servings)


@bp.route("/meal/<meal_key>/add-to-shopping", methods=["POST"])
@login_required
def add_meal_to_shopping(meal_key):
    meal = next((m for m in _all_meals() if m["key"] == meal_key), None)
    servings = request.form.get("servings", type=int, default=1)
    if meal:
        have_at_home = {i.name for i in ShoppingListItem.query.filter_by(
            user_id=current_user.id, have_at_home=True).all()}
        items = generate_shopping_list([(meal, servings)])
        for item in items:
            existing = ShoppingListItem.query.filter_by(
                user_id=current_user.id, name=item["name_en"], checked=False).first()
            if existing:
                existing.quantity = (existing.quantity or 0) + item["qty"]
            else:
                db.session.add(ShoppingListItem(
                    user_id=current_user.id, name=item["name_en"], quantity=item["qty"],
                    unit=item["unit"], category=item["category"], have_at_home=item["have_at_home"],
                ))
        db.session.commit()
        flash("Added to shopping list." if current_user.profile.language != "ro" else "Adăugat în lista de cumpărături.", "success")
    return redirect(url_for("meals.meal_detail", meal_key=meal_key))


@bp.route("/regenerate-day", methods=["POST"])
@login_required
def regenerate_day():
    """Suggest a full day of meals (one per meal-type, scaled in servings
    where needed) that together land close to today's calorie/protein
    targets — see logic.nutrition_engine.suggest_day_plan for why this
    isn't just 'grab the single smallest matching meal per slot' (that
    version used to leave the day's total far under the target)."""
    profile = current_user.profile
    targets = calculate_targets(profile)
    meals = _all_meals()
    recent = recently_eaten_meal_keys(
        [meal_log_to_dict(e) for e in MealLogEntry.query.filter_by(user_id=current_user.id).all()], days=5)

    day_plan = suggest_day_plan(meals, targets["target_calories"], targets["protein_g"],
                                 recently_used_keys=recent)
    plan_total_kcal = sum(m["kcal_total"] for m in day_plan)
    plan_total_protein = round(sum(m["protein_g_total"] for m in day_plan), 1)

    return render_template("meals/day_plan.html", profile=profile, day_plan=day_plan, targets=targets,
                            plan_total_kcal=plan_total_kcal, plan_total_protein=plan_total_protein)


# ---------------------------------------------------------------------------
# Barcode / product scanner
# ---------------------------------------------------------------------------

@bp.route("/scanner")
@login_required
def scanner():
    return render_template("meals/scanner.html", profile=current_user.profile)


@bp.route("/scanner/lookup", methods=["POST"])
@login_required
def scanner_lookup():
    barcode = request.form.get("barcode", "").strip()
    if not barcode.isdigit():
        return jsonify({"found": False, "error": "invalid_barcode"})
    product = fetch_product(barcode)
    if not product.get("found"):
        return jsonify(product)

    profile = current_user.profile
    targets = calculate_targets(profile)
    fit = goal_fit(product, profile.goal, remaining_kcal=targets["target_calories"], lang=profile.language)
    product["fit"] = fit
    return jsonify(product)


@bp.route("/scanner/log", methods=["POST"])
@login_required
def scanner_log():
    profile = current_user.profile
    portion_g = request.form.get("portion_g", type=float, default=100)
    per_100g = {
        "kcal": request.form.get("kcal", type=float),
        "protein_g": request.form.get("protein_g", type=float),
        "carb_g": request.form.get("carb_g", type=float),
        "fat_g": request.form.get("fat_g", type=float),
        "fiber_g": request.form.get("fiber_g", type=float),
    }
    scaled = scale_to_portion(per_100g, portion_g)
    entry = MealLogEntry(
        user_id=current_user.id, date=date.today().isoformat(),
        meal_type=request.form.get("meal_type", "snack"),
        food_key=None, food_name=request.form.get("product_name", "Scanned product"),
        qty=portion_g, unit="g",
        kcal=round(scaled["kcal"] or 0), protein_g=scaled["protein_g"] or 0,
        carb_g=scaled["carb_g"] or 0, fat_g=scaled["fat_g"] or 0, fiber_g=scaled["fiber_g"] or 0,
        source="off", barcode=request.form.get("barcode"),
        estimated=request.form.get("estimated") == "true",
    )
    db.session.add(entry)
    db.session.commit()
    flash("Logged." if profile.language != "ro" else "Înregistrat.", "success")
    return redirect(url_for("meals.index"))


@bp.route("/scanner/manual")
@login_required
def scanner_manual_search():
    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify([])
    profile = current_user.profile
    matches = [f for f in _all_foods()
               if q in f["name_en"].lower() or q in f["name_ro"].lower()][:10]
    return jsonify(matches)


# ---------------------------------------------------------------------------
# Shopping list
# ---------------------------------------------------------------------------

@bp.route("/shopping-list")
@login_required
def shopping_list():
    items = ShoppingListItem.query.filter_by(user_id=current_user.id).order_by(
        ShoppingListItem.category, ShoppingListItem.name).all()
    return render_template("meals/shopping_list.html", profile=current_user.profile, items=items)


@bp.route("/shopping-list/add", methods=["POST"])
@login_required
def shopping_list_add():
    name = request.form.get("name", "").strip()
    if name:
        db.session.add(ShoppingListItem(
            user_id=current_user.id, name=name,
            quantity=request.form.get("quantity", type=float),
            unit=request.form.get("unit", "g"), category=request.form.get("category", "other"),
        ))
        db.session.commit()
    return redirect(url_for("meals.shopping_list"))


@bp.route("/shopping-list/toggle/<int:item_id>", methods=["POST"])
@login_required
def shopping_list_toggle(item_id):
    item = ShoppingListItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if item:
        item.checked = not item.checked
        db.session.commit()
    return redirect(url_for("meals.shopping_list"))


@bp.route("/shopping-list/have/<int:item_id>", methods=["POST"])
@login_required
def shopping_list_have(item_id):
    item = ShoppingListItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if item:
        item.have_at_home = not item.have_at_home
        db.session.commit()
    return redirect(url_for("meals.shopping_list"))


@bp.route("/shopping-list/delete/<int:item_id>", methods=["POST"])
@login_required
def shopping_list_delete(item_id):
    item = ShoppingListItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("meals.shopping_list"))
