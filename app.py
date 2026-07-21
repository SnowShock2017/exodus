"""
app.py
------
Flask application factory for Exodus v2 (multi-user). Registers every
blueprint, sets up the database + login manager, and seeds the shared
libraries (exercises/meals/food items/CrossFit workouts) on first run.

Run locally with:
    python app.py
Deploy to Render + Supabase: see DEPLOY_RENDER.md and SUPABASE_SETUP.md.
"""

import os
from datetime import date

from flask import Flask, render_template
from flask_login import current_user

from config import Config
from extensions import db, login_manager
from models import User
from logic.i18n import t
from logic import seed


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from routes.auth import bp as auth_bp
    from routes.onboarding import bp as onboarding_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.meals import bp as meals_bp
    from routes.workouts import bp as workouts_bp
    from routes.crossfit import bp as crossfit_bp
    from routes.progress import bp as progress_bp
    from routes.assistant import bp as assistant_bp
    from routes.settings import bp as settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(meals_bp)
    app.register_blueprint(workouts_bp)
    app.register_blueprint(crossfit_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(settings_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        lang = "en"
        if current_user.is_authenticated and current_user.profile:
            lang = current_user.profile.language or "en"
        return {"t": lambda key: t(key, lang), "lang": lang, "today": date.today().isoformat()}

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    with app.app_context():
        db.create_all()
        seed.seed_all()

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("EXODUS_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
