# Exodus v2 — Documentation

Exodus is your personal fitness/nutrition/CrossFit web app, built to run as
an installable "app" on your iPhone (Add to Home Screen) with real
accounts, bilingual EN/RO support, and zero recurring cost. This document
explains what was built, how it's organized, and how to change or extend
it later.

This is a full rewrite of the original single-user version into a proper
multi-user app: accounts, a hosted Postgres database, a much bigger meal
and exercise library, a barcode scanner, a CrossFit module, and a rule-based
AI Assistant. If you're looking for the original v1 (single-user, JSON
files, no login), it's superseded — this document only covers v2.

---

## 1. What's actually in this app

**Accounts & onboarding** — email/password signup and login, forgot/reset
password (via email if you configure SMTP, see §8), a 4-step onboarding
wizard that collects goal, body stats, training background, equipment,
and diet preferences, GDPR-style data export (JSON download of everything
tied to your account) and account deletion.

**Goals & targets** — three goal modes (lean out, build muscle, recomp)
with large tap-friendly buttons, calorie/protein/carb/fat/fiber/water
targets computed from your stats (Mifflin-St Jeor BMR + activity
multiplier), and a 10-day gradual ramp whenever you switch goals instead
of an abrupt calorie jump.

**Meals & nutrition** — a 28-recipe library tagged by diet type
(vegetarian, vegan, lactose-free, gluten-free, high-protein, low-carb,
etc.), full macros per serving, ingredient substitutions, step-by-step
instructions in EN and RO, a day-plan generator that fills your remaining
calories/macros with suggested meals, manual food logging against a
26-item food database, a shopping list built from your planned meals
(ingredients auto-combined across recipes), and meal favoriting/rating.

**Barcode scanner** — scan any packaged food's barcode with your phone
camera (via the free `html5-qrcode` library, runs entirely in the
browser) or search by product name; looks the product up against Open
Food Facts (free, no API key, no cost) and shows you calories/macros
per your actual portion size plus a plain-language "fits your remaining
macros" verdict, with one tap to log it.

**Workouts** — pick from 10 training styles (full body, upper/lower,
push/pull/legs, bro split, strength, hypertrophy, powerbuilding,
bodyweight, home, custom), AI-generated weekly plans that avoid repeating
the same accessory exercises week to week (rotates deterministically by
ISO week number so it's still explainable, not random), a 62-exercise
library with EN/RO instructions, breathing cues, common mistakes, safety
tips, easier/harder variations, and injury-based exclusion (tell it about
a knee/shoulder/back issue and it filters those exercises out and
suggests substitutes automatically). Set-by-set logging with automatic PR
detection (via estimated 1RM, Epley formula) and volume tracking per
muscle group.

**CrossFit** — a dedicated CrossFit section with 22 WODs across every
major format (AMRAP, EMOM, For Time, Interval, Strength+Conditioning,
Bodyweight, Partner, Equipment-Free) at 3 difficulty levels, a
"generate me a workout" button that builds a new WOD from your equipment
and level, score logging, and favoriting.

**Progress tracking** — weight trend, estimated-1RM trend per lift,
weekly training volume, workout consistency (days trained vs. planned),
calorie/protein adherence over time, step tracking, and a personal
records list — all rendered as Chart.js graphs, plus a weekly summary.

**Readiness & recovery** — a quick daily check-in (sleep, soreness,
stress, energy) that adjusts today's workout suggestion (e.g. suggests a
lighter session or rest if you're clearly run down).

**AI Assistant** — a chat-style page you can ask things like "what should
I eat before a workout?" or "give me an alternative to squats, my knee
hurts" — this is a **rule-based** assistant (keyword/intent matching, not
an LLM), by design, so it stays free forever and never has an API bill.
It recognizes common exercise nicknames in both languages and cross-
references your injury settings when suggesting alternatives.

**Safety rules** — keyword screening (EN+RO) for red-flag phrases (chest
pain, severe dizziness, etc.) that, if detected anywhere in the app,
short-circuits to a "please seek medical attention" message instead of
fitness advice; a separate check flags dangerously low calorie targets
and nudges back toward a safe minimum instead of encouraging a crash diet.

**Bilingual EN/RO** — every screen, label, and generated message is
available in both languages (218 translation keys), switchable in
Settings.

**Installable "app" feel** — a PWA manifest and home-screen icon so
"Add to Home Screen" on iPhone gives you a real app icon and a full-screen
experience with no Safari address bar.

---

## 2. What was intentionally left out (and why)

Kept out of scope to protect the $0 budget and the "quick to build"
goal — these are legitimate future upgrades, not oversights:

- **Admin dashboard / content management UI.** You can still edit the
  exercise/meal/CrossFit library by editing the JSON files in
  `seed_data/` directly (see §7) — there's just no in-app screen for it.
- **Push notifications.** Would need a paid push service or a lot of
  extra infrastructure; the app relies on you opening it instead.
- **Social login (Google/Apple/Facebook).** Email+password only, to avoid
  OAuth app-review requirements and third-party dependencies.
- **Progress photos.** No image upload/storage was built (would need paid
  object storage at any real scale); weight/lift/volume charts cover
  progress tracking instead.
- **Full OCR nutrition-label reading.** The scanner uses Open Food Facts'
  barcode database, not on-device OCR of ingredient labels — barcode
  coverage in Romania (including most Lidl private-label products) is
  good but not 100%; anything unlisted falls back to manual search/entry.
- **Deload week / mobility programming.** The workout engine handles
  weekly exercise rotation and injury filtering, but doesn't auto-insert
  periodized deload weeks or a dedicated mobility track — worth adding
  later if you want it.

None of these block daily use. If you want any of them built next, say
so and we can scope it the same way this build was scoped.

---

## 3. Architecture overview

```
exodus/
├── app.py                  # Flask app factory — creates the app, registers
│                            # blueprints, sets up DB + login, seeds data
├── config.py                # reads DATABASE_URL (Supabase) or falls back
│                            # to local SQLite; other app settings
├── extensions.py            # shared SQLAlchemy `db` and Flask-Login
│                            # `login_manager` instances
├── models.py                 # every database table (see §4)
├── requirements.txt
├── routes/                  # one Blueprint per app section (see §5)
├── logic/                   # framework-free business logic (see §6)
├── seed_data/                # the exercise/meal/food/CrossFit libraries,
│                            # as editable JSON (see §7)
├── templates/                # Jinja2 HTML templates, one folder per
│                            # section, sharing templates/base.html
├── static/                   # CSS, JS (scanner, manifest, icon)
├── DOCUMENTATION.md           # this file
├── DEPLOY_RENDER.md          # how to get the app live on Render
└── SUPABASE_SETUP.md         # how to set up the free database
```

**Why the logic is separated from Flask.** Every piece of "thinking" the
app does — computing your calorie target, picking this week's exercises,
detecting a PR, generating a CrossFit workout, matching your Assistant
question to an answer — lives in `logic/*.py` as plain Python functions
that take and return ordinary dicts. They never import Flask or
SQLAlchemy. `routes/*.py` is the only place that touches the database or
HTTP — it fetches rows, converts them to dicts (via `logic/helpers.py`),
hands them to the relevant logic function, and saves the result back.

This isn't just tidiness — it's what made this entire app testable in a
sandboxed environment with no internet access (pip install doesn't work
there), because every logic module could be unit-tested directly with
plain `assert` statements, with no server or database required. It also
means if you ever want to swap out a piece — e.g. replace the rule-based
Assistant with a real LLM later — you only touch `logic/assistant_engine.py`
and its one call site in `routes/assistant.py`; nothing else changes.

---

## 4. Database (`models.py`)

Every table has a `user_id` (or belongs to something that does) except
the three shared library tables (`Exercise`, `MealTemplate`, `FoodItem`,
`CrossfitWorkout`) which are the same for every user, seeded once from
`seed_data/`.

| Table | Purpose |
|---|---|
| `User` | email, password hash, admin flag |
| `Profile` | goal, stats, equipment, diet prefs, injuries, targets — one per user |
| `WeightLog`, `StepLog`, `SleepLog` | daily tracking entries |
| `ReadinessCheckin` | daily soreness/sleep/stress/energy check-in |
| `MealLogEntry` | a logged food/meal + when |
| `FavoriteMeal`, `MealRating` | your saved/rated meals |
| `ShoppingListItem` | shopping list rows, combinable across meals |
| `Exercise` | shared exercise library (EN/RO instructions etc.) |
| `MealTemplate` | shared recipe library |
| `FoodItem` | shared manual-log food database |
| `WorkoutPlan` → `WorkoutDay` → `PlanExercise` | your active weekly plan and its exercises |
| `WorkoutSetLog` | every logged set (weight, reps, RPE, date) |
| `CrossfitWorkout` | shared WOD library |
| `CrossfitLog`, `FavoriteCrossfit` | your CrossFit scores/favorites |
| `PasswordResetToken` | short-lived tokens for the forgot-password flow |

**The privacy model, in one sentence:** every query that touches personal
data filters by `current_user.id`, so one account can never see another
account's rows — this is enforced at the query level throughout
`routes/*.py`, not by hiding UI elements.

---

## 5. Routes (URL map)

| Blueprint | Prefix | What it covers |
|---|---|---|
| `auth` | `/` | `/signup`, `/login`, `/logout`, `/forgot-password`, `/reset-password/<token>`, `/account/export`, `/account/delete` |
| `onboarding` | `/onboarding` | `/`, `/step/<1-4>` — the setup wizard |
| `dashboard` | `/` | `/` — home screen (today's targets, quick links) |
| `meals` | `/meals` | library, day-plan, food logging, scanner, shopping list, favorites/ratings |
| `workouts` | `/workouts` | today's session, set logging, plan view/generation, exercise replace, exercise library/detail, readiness check-in |
| `crossfit` | `/crossfit` | WOD library, generate, detail, score logging, favorites |
| `progress` | `/progress` | all charts and the weekly summary |
| `assistant` | `/assistant` | the chat-style AI Assistant page |
| `settings` | `/settings` | profile/goal/equipment/diet editing |

Every route (except `auth` signup/login/forgot-password and the 404
handler) requires `@login_required` — the whole app is behind a login.

---

## 6. Logic engines (`logic/`)

| File | What it does |
|---|---|
| `goal_engine.py` | goal params, 10-day ramped calorie/macro transitions, target calculation |
| `nutrition_engine.py` | food logging, meal browsing/filtering/scaling, shopping-list generation |
| `off_client.py` | Open Food Facts response parsing, portion scaling, "fits your macros" verdict |
| `workout_engine.py` | weekly plan building (10 styles), week-to-week exercise rotation, replacement suggestions, e1RM/PR detection, volume-by-muscle |
| `crossfit_engine.py` | WOD filtering/scaling, deterministic "generate a workout" logic |
| `progress_engine.py` | every chart series + weekly summary |
| `safety.py` | red-flag keyword screening (EN+RO), low-calorie warning, readiness-based suggestions |
| `assistant_engine.py` | intent matching, exercise-alias recognition, the Assistant's answers |
| `i18n.py` | the EN/RO translation dictionary (`t(key, lang)`) |
| `seed.py` | loads `seed_data/*.json` into the database on first run |
| `helpers.py` | converts SQLAlchemy rows → plain dicts for the logic engines |
| `emailer.py` | optional SMTP password-reset email (see §8) |
| `cache.py` | in-memory cache for the shared exercise/meal/food/CrossFit libraries — see the performance note below |

Two orphaned v1 modules (`logic/profile_store.py`, `logic/coach_engine.py`,
`logic/supplement_engine.py`) are still in the folder from the original
single-user build but are no longer imported anywhere in v2 — safe to
ignore or delete, kept only because files in this workspace can't be
auto-deleted.

---

## 6.1 Performance: why pages were slow, and what changed

Early versions of every route queried the shared exercise/meal/food/CrossFit
tables fresh on every page load — and in a few places (`workouts.today()`,
`crossfit.detail()`) did so once per row inside a Python loop, a classic
N+1 pattern. Each of those is a real network round trip to Postgres; on a
free-tier host, ten to twenty sequential round trips per page is exactly
what a multi-second page-to-page lag looks like.

`logic/cache.py` now loads those four shared tables into memory once per
running process and serves every read from a plain dict afterward. They
only need reloading after a fresh deploy (new process = empty cache), so
this is safe with no staleness risk in normal use. If you ever add a way
to edit the shared library from inside a running app, call
`logic.cache.clear()` afterward.

`config.py` also sets `pool_pre_ping` and `pool_recycle` on the database
engine, since free-tier Postgres poolers can silently drop idle
connections — without this, the first request after any idle period could
fail instead of transparently reconnecting.

If pages are still slow after this, check that your Render service and
Supabase project are in the same or nearby region (Settings on each) —
cross-region round trips add real latency that no amount of query
optimization can remove.

## 7. Editing the content library (no code changes needed)

Exercises, meals, food items, and CrossFit workouts all live as JSON in
`seed_data/`. To add or change one:

1. Open the relevant file (`seed_data/exercises.json`, `meals.json`,
   `food_db.json`, or `crossfit_workouts.json`).
2. Copy an existing entry as a template — every entry in a file shares
   the same fields — and edit the values (fill in both `_en` and `_ro`
   fields for anything that has them).
3. Commit/upload the changed file to GitHub (see `DEPLOY_RENDER.md` Part
   4). `logic/seed.py` only inserts rows that aren't already in the
   database (matched by `key`), so new entries appear automatically after
   a redeploy — but **editing an existing entry's fields won't retroactively
   update rows already seeded into your database**; for a content edit to
   take effect you'd currently need to delete that row from Supabase's
   Table Editor (or wipe and reseed) so `seed_data`'s version reloads. This
   is a fine tradeoff for occasional edits; ask if you want an "always
   overwrite from seed_data" mode instead.

---

## 8. Optional: password-reset emails

By default, "forgot password" still works, but the reset link only shows
up in the server logs (fine for solo use). To have it emailed instead,
set these environment variables on Render (Environment tab, same place as
`DATABASE_URL`):

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your.email@gmail.com
SMTP_PASSWORD=<a Gmail App Password, not your real password>
```

A Gmail **App Password** is free — generate one at
myaccount.google.com → Security → 2-Step Verification → App Passwords.
`logic/emailer.py` checks whether these are set (`smtp_configured()`) and
silently falls back to log-only if they're not, so this step is entirely
optional.

---

## 9. Common changes — where to look

| You want to... | Edit this |
|---|---|
| Change how calories/macros are calculated | `logic/goal_engine.py` |
| Add a new goal mode | `logic/goal_engine.py` (`GOAL_PARAMS`, `GOAL_LABELS`, `GOAL_DESCRIPTIONS`) + `templates/settings.html` goal buttons |
| Add exercises, meals, foods, WODs | `seed_data/*.json` (see §7) |
| Add a new training style | `logic/workout_engine.py` (`STYLE_CONFIG`) |
| Change PR / 1RM math | `logic/workout_engine.py` (`estimate_1rm`, `detect_pr`) |
| Add red-flag safety keywords | `logic/safety.py` |
| Teach the Assistant a new question type | `logic/assistant_engine.py` (`_match_intent`, `QUICK_QUESTIONS`) |
| Add/change a translation | `logic/i18n.py` (keep EN and RO keys in sync) |
| Change colors/fonts/layout | `static/css/style.css` |
| Add a new page | new template in `templates/<section>/`, new route in `routes/<section>.py`, register in `app.py` if it's a new blueprint |

---

## 10. Testing notes

This app was built and verified without ever running a live server
locally (the build sandbox has no outbound network access, so
`pip install` wasn't possible there). Verification instead relied on:

- `python3 -m py_compile` on every `.py` file (confirms syntax/imports
  are valid).
- Hand-written unit tests (plain `assert`) exercising every function in
  every `logic/*.py` engine — goal ramping, macro math, workout
  generation and rotation, PR detection, CrossFit generation, safety
  keyword matching (including the EN/RO fix noted below), and Assistant
  intent matching.
- A standalone Jinja2 rendering harness that rendered all 24 templates
  with mocked data (both languages, empty/populated states) to catch
  template errors before deploy.

Two real bugs were caught and fixed this way: a Romanian red-flag phrase
that only matched the singular form ("durere în piept") and missed the
plural ("dureri în piept") — fixed by adding common variants; and the
Assistant failing to recognize casual exercise names like "squats" or
"bench" (it only matched full canonical names) — fixed by adding an alias
dictionary. Both are now covered by passing tests.

Once you have the app running for real (locally or on Render), it's
worth clicking through signup → onboarding → logging a meal → logging a
workout set → the Assistant once, just to see it live — the sandbox
testing above catches logic and syntax errors, not visual/UX issues.

---

## 11. Getting it live

See **`DEPLOY_RENDER.md`** (GitHub + Render, free, https) and
**`SUPABASE_SETUP.md`** (free hosted Postgres database) for the full
step-by-step. Short version: push this folder to GitHub, connect it to a
free Render web service, set `DATABASE_URL` to a free Supabase Postgres
connection string, and open the resulting `https://...onrender.com` URL
on your iPhone and "Add to Home Screen."
