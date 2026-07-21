"""
models.py
---------
All database tables (SQLAlchemy models) for the multi-user version of
Exodus. Works identically against local SQLite (dev) and Supabase/Postgres
(production) — see config.py.

Every table that holds personal data has a `user_id` foreign key, and every
query in the route files filters by `current_user.id`. That's the whole
privacy model: nobody's data query can return rows belonging to a
different user_id, because we never write a query without that filter.
See DOCUMENTATION.md section "Privacy & multi-user data isolation" for the
full explanation.

Shared/global tables (Exercise, MealTemplate, CrossfitWorkout) have no
user_id — they're a library everyone reads from, seeded once from
seed_data/*.json (see logic/seed.py).
"""

from datetime import datetime, date

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    profile = db.relationship("Profile", backref="user", uselist=False,
                               cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Profile(db.Model):
    __tablename__ = "profiles"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)

    name = db.Column(db.String(120), default="")
    age = db.Column(db.Integer, default=25)
    sex = db.Column(db.String(10), default="male")  # male / female / unspecified
    height_cm = db.Column(db.Float, default=175)
    weight_kg = db.Column(db.Float, default=75)
    target_weight_kg = db.Column(db.Float, nullable=True)

    goal = db.Column(db.String(30), default="lean_maintain_strength")
    # lean_maintain_strength | maintenance | muscle_gain

    experience_level = db.Column(db.String(20), default="beginner")  # beginner/intermediate/advanced
    activity_level = db.Column(db.String(20), default="moderate")     # sedentary/moderate/high
    training_days_per_week = db.Column(db.Integer, default=4)
    preferred_style = db.Column(db.String(30), default="upper_lower")
    # full_body | upper_lower | push_pull_legs | bro_split | strength | hypertrophy |
    # powerbuilding | bodyweight | home | custom

    equipment = db.Column(db.JSON, default=list)          # e.g. ["barbell","dumbbell","pullup_bar"]
    dietary_prefs = db.Column(db.JSON, default=list)      # e.g. ["vegetarian"]
    allergies = db.Column(db.JSON, default=list)          # e.g. ["peanuts","lactose"]
    dislikes = db.Column(db.JSON, default=list)           # free-text disliked foods
    injuries = db.Column(db.Text, default="")             # free text + tags parsed for avoid_if_injury matching
    injury_tags = db.Column(db.JSON, default=list)        # e.g. ["knee","shoulder"]

    language = db.Column(db.String(2), default="en")      # en / ro
    units = db.Column(db.String(2), default="kg")         # kg / lb
    meal_frequency = db.Column(db.Integer, default=4)
    sleep_hours = db.Column(db.Float, default=7.5)
    step_target = db.Column(db.Integer, nullable=True)

    prs_kg = db.Column(db.JSON, default=dict)  # {"bench":100,"squat":80,"deadlift":100,"pullups_clean_reps":12}

    return_to_training_start_date = db.Column(db.String(10), nullable=True)  # YYYY-MM-DD, ramp phase anchor

    goal_changed_at = db.Column(db.String(10), nullable=True)
    goal_transition_from_calories = db.Column(db.Integer, nullable=True)

    onboarding_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WeightLog(db.Model):
    __tablename__ = "weight_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)


class StepLog(db.Model):
    __tablename__ = "step_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False)
    steps = db.Column(db.Integer, nullable=False)


class SleepLog(db.Model):
    __tablename__ = "sleep_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False)
    hours = db.Column(db.Float, nullable=False)
    quality = db.Column(db.Integer, nullable=True)  # 1-5


class ReadinessCheckin(db.Model):
    __tablename__ = "readiness_checkins"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False)
    energy = db.Column(db.Integer)       # 1-5
    sleep_quality = db.Column(db.Integer)  # 1-5
    soreness = db.Column(db.Integer)     # 1-5
    stress = db.Column(db.Integer)       # 1-5
    available_minutes = db.Column(db.Integer)
    pain_notes = db.Column(db.Text, default="")
    suggested_action = db.Column(db.String(30))  # as_planned/reduce_weight/reduce_sets/lighter/rest
    chosen_action = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MealLogEntry(db.Model):
    __tablename__ = "meal_log_entries"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False)
    meal_type = db.Column(db.String(20), default="snack")
    food_key = db.Column(db.String(60), nullable=True)
    food_name = db.Column(db.String(200), nullable=False)
    qty = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(10), default="g")
    kcal = db.Column(db.Integer, default=0)
    protein_g = db.Column(db.Float, default=0)
    carb_g = db.Column(db.Float, default=0)
    fat_g = db.Column(db.Float, default=0)
    fiber_g = db.Column(db.Float, default=0)
    source = db.Column(db.String(10), default="db")  # db | off | custom
    barcode = db.Column(db.String(30), nullable=True)
    estimated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FavoriteMeal(db.Model):
    __tablename__ = "favorite_meals"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    meal_key = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "meal_key"),)


class MealRating(db.Model):
    __tablename__ = "meal_ratings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    meal_key = db.Column(db.String(60), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    __table_args__ = (db.UniqueConstraint("user_id", "meal_key"),)


class ShoppingListItem(db.Model):
    __tablename__ = "shopping_list_items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Float, nullable=True)
    unit = db.Column(db.String(10), default="g")
    category = db.Column(db.String(30), default="other")
    checked = db.Column(db.Boolean, default=False)
    have_at_home = db.Column(db.Boolean, default=False)
    est_price = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Exercise(db.Model):
    """Shared exercise library — no user_id, seeded from seed_data/exercises.json."""
    __tablename__ = "exercises"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False, index=True)
    name_en = db.Column(db.String(120))
    name_ro = db.Column(db.String(120))
    primary_muscle = db.Column(db.String(40))
    secondary_muscles = db.Column(db.JSON, default=list)
    equipment = db.Column(db.JSON, default=list)
    movement_pattern = db.Column(db.String(30))
    experience_level = db.Column(db.String(20), default="beginner")
    unilateral = db.Column(db.Boolean, default=False)
    instructions_en = db.Column(db.JSON, default=list)
    instructions_ro = db.Column(db.JSON, default=list)
    breathing_en = db.Column(db.Text, default="")
    breathing_ro = db.Column(db.Text, default="")
    common_mistakes_en = db.Column(db.JSON, default=list)
    common_mistakes_ro = db.Column(db.JSON, default=list)
    safety_tips_en = db.Column(db.JSON, default=list)
    safety_tips_ro = db.Column(db.JSON, default=list)
    easier_variation = db.Column(db.String(60), nullable=True)
    harder_variation = db.Column(db.String(60), nullable=True)
    avoid_if_injury = db.Column(db.JSON, default=list)


class MealTemplate(db.Model):
    """Shared meal-idea/recipe library — no user_id, seeded from seed_data/meals.json."""
    __tablename__ = "meal_templates"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False, index=True)
    name_en = db.Column(db.String(150))
    name_ro = db.Column(db.String(150))
    tags = db.Column(db.JSON, default=list)
    base_servings = db.Column(db.Integer, default=1)
    prep_time_min = db.Column(db.Integer, default=15)
    difficulty = db.Column(db.String(10), default="easy")
    ingredients = db.Column(db.JSON, default=list)
    kcal_per_serving = db.Column(db.Integer, default=0)
    protein_g_per_serving = db.Column(db.Float, default=0)
    carb_g_per_serving = db.Column(db.Float, default=0)
    fat_g_per_serving = db.Column(db.Float, default=0)
    fiber_g_per_serving = db.Column(db.Float, default=0)
    substitutions_en = db.Column(db.JSON, default=list)
    substitutions_ro = db.Column(db.JSON, default=list)
    steps_en = db.Column(db.JSON, default=list)
    steps_ro = db.Column(db.JSON, default=list)


class FoodItem(db.Model):
    """Shared simple-food database (per 100g/unit) — seeded from seed_data/food_db.json."""
    __tablename__ = "food_items"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False, index=True)
    name_en = db.Column(db.String(150))
    name_ro = db.Column(db.String(150))
    unit = db.Column(db.String(10), default="g")
    per = db.Column(db.Float, default=100)
    kcal = db.Column(db.Float, default=0)
    protein = db.Column(db.Float, default=0)
    carb = db.Column(db.Float, default=0)
    fat = db.Column(db.Float, default=0)
    fiber = db.Column(db.Float, default=0)


class WorkoutPlan(db.Model):
    __tablename__ = "workout_plans"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), default="My plan")
    style = db.Column(db.String(30), default="upper_lower")
    week_start_date = db.Column(db.String(10), nullable=True)  # Monday of the week this plan covers
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    days = db.relationship("WorkoutDay", backref="plan", cascade="all, delete-orphan",
                            order_by="WorkoutDay.weekday_index")


class WorkoutDay(db.Model):
    __tablename__ = "workout_days"
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("workout_plans.id"), nullable=False, index=True)
    weekday_index = db.Column(db.Integer, nullable=False)  # 0=Mon ... 6=Sun
    label = db.Column(db.String(80), default="")
    is_rest = db.Column(db.Boolean, default=False)

    exercises = db.relationship("PlanExercise", backref="day", cascade="all, delete-orphan",
                                 order_by="PlanExercise.order_index")


class PlanExercise(db.Model):
    __tablename__ = "plan_exercises"
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("workout_days.id"), nullable=False, index=True)
    exercise_key = db.Column(db.String(60), nullable=False)
    order_index = db.Column(db.Integer, default=0)
    sets = db.Column(db.Integer, default=3)
    reps = db.Column(db.String(20), default="8-10")  # text so ranges like "8-10" or "AMRAP" work
    target_weight_kg = db.Column(db.Float, nullable=True)
    rest_seconds = db.Column(db.Integer, default=90)
    tempo = db.Column(db.String(20), nullable=True)
    warmup_sets = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, default="")
    is_main_lift = db.Column(db.Boolean, default=False)


class WorkoutSetLog(db.Model):
    __tablename__ = "workout_set_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False)
    exercise_key = db.Column(db.String(60), nullable=False, index=True)
    plan_exercise_id = db.Column(db.Integer, db.ForeignKey("plan_exercises.id"), nullable=True)
    set_number = db.Column(db.Integer, default=1)
    weight_kg = db.Column(db.Float, nullable=True)
    reps_done = db.Column(db.Integer, nullable=True)
    rpe = db.Column(db.Float, nullable=True)
    rir = db.Column(db.Integer, nullable=True)
    is_warmup = db.Column(db.Boolean, default=False)
    completed = db.Column(db.String(15), default="completed")  # completed/skipped/partial/replaced
    notes = db.Column(db.Text, default="")
    pain = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CrossfitWorkout(db.Model):
    """Shared CrossFit template library — seeded from seed_data/crossfit_workouts.json."""
    __tablename__ = "crossfit_workouts"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False, index=True)
    name_en = db.Column(db.String(150))
    name_ro = db.Column(db.String(150))
    type = db.Column(db.String(30))
    difficulty = db.Column(db.String(15))
    equipment = db.Column(db.JSON, default=list)
    target_muscles = db.Column(db.JSON, default=list)
    est_duration_min = db.Column(db.Integer, default=15)
    format_en = db.Column(db.Text, default="")
    format_ro = db.Column(db.Text, default="")
    movements = db.Column(db.JSON, default=list)
    scaling_notes_en = db.Column(db.Text, default="")
    scaling_notes_ro = db.Column(db.Text, default="")
    technique_notes_en = db.Column(db.Text, default="")
    technique_notes_ro = db.Column(db.Text, default="")


class CrossfitLog(db.Model):
    __tablename__ = "crossfit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False)
    workout_key = db.Column(db.String(60), nullable=False)
    score_text = db.Column(db.String(80), default="")
    difficulty_used = db.Column(db.String(15), default="")
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FavoriteCrossfit(db.Model):
    __tablename__ = "favorite_crossfit"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    workout_key = db.Column(db.String(60), nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "workout_key"),)


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used = db.Column(db.Boolean, default=False)
