"""
routes/assistant.py
--------------------
The AI Assistant chat page. Stateless per-request (no conversation memory
stored) — every message is answered fresh from the user's current data.
See logic/assistant_engine.py for the actual intent routing.
"""

from datetime import date

from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from models import MealLogEntry
from logic.helpers import profile_to_dict, meal_log_to_dict
from logic.cache import get_meals, get_exercises
from logic.goal_engine import calculate_targets
from logic.assistant_engine import answer, QUICK_QUESTIONS

bp = Blueprint("assistant", __name__, url_prefix="/assistant")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    profile = current_user.profile
    response = None
    message = ""

    if request.method == "POST":
        message = request.form.get("message", "").strip()
        if message:
            targets = calculate_targets(profile)
            meal_log_today = [meal_log_to_dict(e) for e in MealLogEntry.query.filter_by(
                user_id=current_user.id, date=date.today().isoformat()).all()]
            all_meals = get_meals()
            all_exercises = get_exercises()

            response = answer(message, profile.language, profile_to_dict(profile), targets,
                               meal_log_today, all_meals, all_exercises)

    return render_template("assistant.html", profile=profile, response=response,
                            message=message, quick_questions=QUICK_QUESTIONS)
