# Exodus — Documentation

Your personal workout + nutrition coach, built in Python (Flask), running as a
mobile web app you can add to your iPhone Home Screen. No AI API, no
subscription, no data leaving your own computer.

This document explains: how to get it running, how to use it, what every
file/function does, and exactly what to edit if you want to change something.

---

## 1. Get it running (step by step)

You need Python 3.10+ on the computer you'll run the server from (your
laptop/desktop — the iPhone is just the screen you view it on, for now).

1. Copy the `exodus/` folder to your computer.
2. Open a terminal in that folder.
3. Install the one dependency:
   ```
   pip install -r requirements.txt
   ```
4. Run it:
   ```
   python app.py
   ```
   You'll see something like `Running on http://0.0.0.0:5050`.
5. Find your computer's local IP address (so your phone can reach it over WiFi):
   - **Mac**: `ipconfig getifaddr en0` (or `en1` if on `en0` gives nothing)
   - **Windows**: `ipconfig` → look for "IPv4 Address" under your WiFi adapter
   - **Linux**: `hostname -I`
   It'll look like `192.168.1.23`.
6. On your **iPhone**, connect to the **same WiFi network**, open Safari, and go to:
   ```
   http://192.168.1.23:5050
   ```
   (replace with your actual IP).
7. Tap the **Share button** → **Add to Home Screen**. Now you have an "Exodus"
   icon on your phone that opens full-screen, like a real app.

> Your computer needs to be on and running `python app.py` for the phone to
> reach it — this is the "local only" setup you asked for. Section 8 below
> covers putting it permanently on the internet later, with no code changes
> needed.

### First thing to do: check your profile

Your stats (190cm, 101kg, PRs: bench 100 / deadlift 100 / squat 80 / 12 clean
pull-ups, 4 days/week) are already pre-filled in `data/user_profile.json`. Open
the **Settings** tab in the app to confirm everything, and correct your exact
age/weight whenever they change (weight also updates automatically whenever
you log it on the Progress tab).

---

## 2. What it actually does

**Dashboard** — today's prescribed workout (or "rest day"), your calorie/macro
target for today, and a list of coach tips generated from your logged data.

**Workout tab** — a 4-day Upper/Lower split whose main lift stays fixed
(that's what makes progression trackable) but whose *accessory* exercises
rotate every calendar week so it doesn't feel like the same routine forever.
Includes a log form for today's main lift (weight, reps per set, RPE) and a
full weekly schedule showing every day's exercises, current and upcoming.

**Meals tab** — your calorie/macro targets with live progress bars showing
how much you've logged today vs. target, a food-logging form (type a food
name, pick a quantity and meal type, hit Add), today's logged items with the
ability to remove any of them, plus meal ideas and your supplement stack.

**Progress tab** — log your body weight, see a weight history table + chart,
a 14-day calorie history chart (bars vs. your target line), and your full
workout log.

**Settings tab** — edit your stats, PRs, goal, training days, and switch
language. (There's also an EN/RO button in the top-right on every page.)

---

## 3. The training plan logic

### Weekly split (fixed 4 days, matching your 4x/week)

| Day | Workout |
|---|---|
| Monday | Upper A — bench-focused strength |
| Tuesday | Lower A — squat-focused strength |
| Wednesday | Rest |
| Thursday | Upper B — pull-ups / back, more hypertrophy volume |
| Friday | Lower B — deadlift-focused strength |
| Saturday / Sunday | Rest |

This is defined in `logic/workout_engine.py` in `WEEKDAY_TO_SPLIT`. If you
want different days (say you prefer training Tue/Wed/Fri/Sat), just change
the numbers there — `0` = Monday ... `6` = Sunday.

### Return-to-training ramp (because you've had a month off)

Coming back at your old 100kg bench / 100kg deadlift / 80kg squat numbers
after a month off is how people tweak elbows, lower backs, and shoulders —
tendons and connective tissue lag behind what your muscles remember. So for
the **first 3 weeks**, Exodus deliberately prescribes lighter weights:

| Week | % of your old PR | Sets x Reps |
|---|---|---|
| 1 | 70% | 3x8 |
| 2 | 80% | 3x6 |
| 3 | 85% | 4x5 |
| 4+ | normal progression | 4x5, see below |

The clock starts from `return_to_training_start_date` in your profile
(currently set to today). This logic lives in `get_phase()` in
`workout_engine.py`.

### Normal progression (double progression)

Once the ramp is done, each main lift uses a simple rule: if your **last**
logged session hit the prescribed reps on every set at RPE 8 or below, the
next session's target weight goes up (+2.5kg bench, +5kg squat/deadlift).
If you missed reps or it was too hard (RPE 9+), it repeats the same weight.
Pull-ups progress the same way but by reps first, then a note suggests adding
a small weight once you're past your old rep PR. This logic is in
`_next_main_lift_weight()` and `_next_pullup_target()`.

**Why rule-based instead of an AI model deciding weights:** it's fully
transparent — you can always see *why* a weight was suggested, and it costs
nothing to run.

### Weekly-rotating accessories

The main lift (bench/squat/pull-ups/deadlift) never changes week to week —
that consistency is what makes the progression math above work. But the
*accessory* movements (the smaller exercises after the main lift) rotate
automatically so the plan doesn't feel identical every week.

Each accessory "slot" (e.g. chest, back, shoulders, calves, core) has 2-3
interchangeable exercise options defined in `ACCESSORY_POOLS` in
`workout_engine.py`. Which option shows up is `ISO calendar week number %
pool size` — so it's fully deterministic (refreshing the page shows the same
plan), guaranteed to differ from last week whenever a pool has 2+ options,
and needs zero stored history to work. A 3-option pool repeats every 3 weeks,
which is a normal rotation length even in real coaching programs.

The Workout tab's "Weekly split" section shows the exercises for every day
of the *current* week, main lift and rotating accessories included, so you
can see your whole week at a glance.

---

## 4. The nutrition logic & daily food logging

`logic/nutrition_engine.py` → `calculate_targets()`:

1. **BMR** (calories your body burns at rest) via the Mifflin-St Jeor formula,
   using your current height/weight/age.
2. **TDEE** (total daily burn) = BMR × an activity multiplier (1.55 for your
   "moderate" setting — training 3-5x/week plus normal daily life).
3. **Calorie target** = TDEE minus an 18% deficit. This is intentionally
   *moderate*, not aggressive — a big deficit is the #1 cause of losing
   strength/muscle while cutting, which conflicts with your goal of staying
   lean **and** keeping your lifts up.
4. **Protein**: 2.2 g per kg body weight — high, to protect muscle during
   the deficit.
5. **Fat**: 0.8 g per kg — enough for hormone health.
6. **Carbs**: whatever calories are left, since carbs are what actually fuel
   your training sessions.

All numbers recalculate automatically whenever your logged weight changes.

Meal ideas (`MEAL_IDEAS` in the same file) are simple, common Romanian-
accessible foods (piept de pui, brânză de vaci, ouă, orez, cartofi, etc.),
each with a bilingual label.

### Logging what you actually eat

The **Meals tab** has a food log, not just a meal-idea list. Type a food name
into the box (it autocompletes from `data/food_db.json`, ~26 common foods
with macros per 100g or per unit), enter a quantity, pick a meal type
(breakfast/lunch/dinner/snack), and hit Add. Exodus looks the food up,
scales its macros by your quantity, and stores the *computed* numbers in
`data/meal_log.json` — so editing the food database later never rewrites
your history.

The top of the Meals tab shows today's running totals against your targets
as progress bars (green under 100%, red once you've gone over) for calories,
protein, carbs, and fat — and the Dashboard shows the same calorie bar at a
glance. The Progress tab adds a 14-day bar chart of logged calories against
your target line, so you can see trends, not just today.

**Adding a food that isn't in the list:** open `data/food_db.json` and add
an entry following the existing pattern (see section 8 below).

**Correcting a mistake:** every logged item on the Meals tab has a Remove
button next to it.

---

## 5. Supplements

`logic/supplement_engine.py` lists a short, conservative stack: creatine
(5g/day), whey protein (only to fill your protein gap), vitamin D3 (2000-4000
IU/day — genuinely relevant in Romania's low-sun autumn/winter), omega-3,
magnesium, and optional caffeine pre-workout. Every recommendation includes a
one-line "why."

**This is general information, not medical advice** — the app always shows
this disclaimer on the Meals tab. Check with a doctor before starting
anything new, especially if you take medication.

---

## 6. The "coach" (adaptive tips)

`logic/coach_engine.py` → `analyze()` runs a few plain rules over your logged
weight and workouts, no AI call involved:

- **Losing weight too fast** (>~1.2%/week) → flags risk to muscle/strength,
  suggests adding calories.
- **Weight has plateaued** → suggests a small calorie cut or extra walking.
- **Healthy pace** → tells you it's working, keep going.
- **Missed sessions** → if you logged fewer sessions than your
  `training_days_per_week` in the last 7 days, it says so.
- **Strength trending down** on bench/squat/deadlift between your last two
  logged sessions → flags to check sleep/protein/calories.
- **Ramp phase reminder** → explains why weights look lighter than your PRs
  right now.

To add a new rule, add a new check inside `analyze()` — it just appends
another string to the `tips` list (write both an English and Romanian
version, see the existing pattern).

---

## 7. File-by-file map

```
exodus/
├── app.py                     Flask routes — the only file that talks HTTP
├── requirements.txt            Flask + gunicorn
├── data/                       Your actual data, plain JSON files
│   ├── user_profile.json       Stats, goal, PRs, language — one dict
│   ├── weight_log.json         List of {date, weight_kg}
│   ├── workout_log.json        List of logged sets per exercise/date
│   ├── meal_log.json           List of logged food entries (see section 4)
│   └── food_db.json            ~26 foods with macros per 100g/unit
├── logic/                       All the "brain" — no Flask/HTTP code here
│   ├── i18n.py                  EN/RO text dictionary + t(key, lang)
│   ├── profile_store.py         Read/write the JSON files above
│   ├── workout_engine.py        Split, ramp phase, progression, accessory rotation
│   ├── nutrition_engine.py      TDEE/macros, meal ideas, food lookup + logging math
│   ├── supplement_engine.py     Supplement list + doses
│   └── coach_engine.py          Rule-based tips from your logs
├── templates/                   HTML pages (Jinja2, rendered by Flask)
│   ├── base.html                Shared header/nav, all pages extend this
│   ├── index.html                Dashboard incl. today's calorie bar
│   ├── workout.html              Today's workout + log form + full week view
│   ├── meals.html                Targets/bars + food log form + food history + supplements
│   ├── progress.html             Weight chart + calorie history chart + workout log
│   └── settings.html             Edit profile form
└── static/
    ├── css/style.css             All styling (dark theme, mobile-first, progress bars)
    ├── js/app.js                 Currently unused placeholder
    ├── manifest.json             PWA metadata (Home Screen icon/name)
    └── icons/icon.png            Home Screen icon
```

**Data is stored as JSON files, not a database.** For one person this is
simpler to inspect/edit by hand and there's nothing to configure. Back these
files up occasionally (e.g. copy the `data/` folder to iCloud Drive or the
Files app) since a fresh reinstall or lost laptop would otherwise lose your
history.

---

## 8. Step by step: what to change for common requests

**Change your training days/schedule**
→ Edit `WEEKDAY_TO_SPLIT` in `logic/workout_engine.py`.

**Change the deficit % or activity multiplier**
→ Edit `DEFICIT_BY_GOAL` / `ACTIVITY_MULTIPLIERS` in `logic/nutrition_engine.py`.

**Add a meal idea**
→ Add a new dict to `MEAL_IDEAS` in `logic/nutrition_engine.py` (needs `en`,
`ro`, `tag`, `protein_note`).

**Add/change a supplement**
→ Add a new dict to the list returned by `get_recommendations()` in
`logic/supplement_engine.py`.

**Add a food to the log's autocomplete list**
→ Add an entry to `data/food_db.json`: `key` (unique id), `name_en`,
`name_ro`, `unit` (`"g"` or `"unit"`), `per` (100 for grams, 1 for units),
and `kcal`/`protein`/`carb`/`fat` for that amount. Look at an existing entry
for the exact shape.

**Change accessory exercise options / add more variety**
→ Edit `ACCESSORY_POOLS` in `logic/workout_engine.py`. Each slot's `options`
list can have as many exercises as you want — more options means a longer
rotation before anything repeats.

**Change how many days the calorie history chart shows**
→ Change `days=14` in the `calorie_history()` call inside the `/progress`
route in `app.py`.

**Add a new coach rule**
→ Add a new `if` block inside `analyze()` in `logic/coach_engine.py`,
appending both an English and Romanian tip string.

**Add a new UI language string**
→ Add the key to *both* the `"en"` and `"ro"` blocks in `logic/i18n.py`, then
use `{{ t('your_key') }}` in any template.

**Edit your stats/PRs without opening the app**
→ Directly edit `data/user_profile.json` (it's plain text).

---

## 9. Deploying to Render (free, gives you https)

Full click-by-click steps are in `DEPLOY_RENDER.md`. Short version:

1. Put the `exodus/` folder in a GitHub repo (web upload, no git required).
2. Render → New Web Service → connect that repo.
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
   - Instance type: Free
3. Render gives you a public `https://your-app.onrender.com` URL — open that
   on your phone (works even when your computer is off) and Add to Home Screen.
4. Free tier sleeps after 15 min of no traffic; the first request after that
   takes ~30-60s to wake back up. Normal, not a bug.
5. (Optional, for privacy) add a simple password check in `app.py` before
   sharing the URL with anyone, since right now anyone with the link could
   see your data.

---

## 10. Limitations (be aware)

- This is **rule-based**, not a real AI model — the "coach" logic is a fixed
  set of if/then checks, which is transparent and free but won't catch
  everything a human coach would.
- No authentication — fine for local-only use; add a login before deploying
  publicly.
- JSON files aren't a real database — perfectly fine for one user's data, but
  don't expect this to scale to multiple users without a rewrite to something
  like SQLite.
- Nutrition/supplement content is general guidance, not medical advice.
