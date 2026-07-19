"""
coach_engine.py
----------------
The "adaptive" part of Exodus. It doesn't call any AI/LLM -- it just runs
a handful of clear, explainable rules over your logged data and returns a
list of short bilingual tips. Add more rules by appending to `analyze()`.

Rules implemented
------------------
1. Weight trend vs. goal: warns if losing weight too fast (risk to muscle/
   strength) or too slowly/plateaued (deficit may need a small tweak).
2. Training consistency: flags missed sessions vs. the planned 4/week.
3. Strength trend: flags if a main lift's working weight dropped between
   the last two logged sessions (possible under-recovery/fatigue).
4. Ramp-phase reminder: explains the current return-to-training phase.
5. First-use nudge: if there's no data yet, tells the user to start logging.
"""

from datetime import date, datetime, timedelta

from logic.workout_engine import get_phase


def _weight_trend(weight_log, days=14):
    if len(weight_log) < 2:
        return None
    cutoff = date.today() - timedelta(days=days)
    recent = [w for w in weight_log if datetime.strptime(w["date"], "%Y-%m-%d").date() >= cutoff]
    if len(recent) < 2:
        recent = weight_log[-2:]
    recent.sort(key=lambda w: w["date"])
    start_w = recent[0]["weight_kg"]
    end_w = recent[-1]["weight_kg"]
    span_days = max((datetime.strptime(recent[-1]["date"], "%Y-%m-%d").date()
                      - datetime.strptime(recent[0]["date"], "%Y-%m-%d").date()).days, 1)
    weekly_rate_pct = ((end_w - start_w) / start_w) * 100 * (7 / span_days)
    return weekly_rate_pct


def _sessions_last_7_days(workout_log):
    cutoff = date.today() - timedelta(days=7)
    dates = set()
    for e in workout_log:
        try:
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        if d >= cutoff:
            dates.add(d)
    return len(dates)


def _strength_trend_flags(workout_log):
    flags = []
    by_lift = {}
    for e in workout_log:
        key = e.get("exercise_key")
        if key in ("bench", "squat", "deadlift"):
            by_lift.setdefault(key, []).append(e)
    for lift, entries in by_lift.items():
        dates = sorted(set(e["date"] for e in entries))
        if len(dates) < 2:
            continue
        last_two = dates[-2:]
        w_prev = max(e["weight_kg"] for e in entries if e["date"] == last_two[0] and e.get("weight_kg"))
        w_last = max(e["weight_kg"] for e in entries if e["date"] == last_two[1] and e.get("weight_kg"))
        if w_last < w_prev:
            flags.append(lift)
    return flags


def analyze(profile, weight_log, workout_log, lang="en"):
    tips = []
    is_ro = lang == "ro"

    if not weight_log and not workout_log:
        tips.append(
            "Log your body weight and today's sets to get real coaching tips here — "
            "right now there's no data yet." if not is_ro else
            "Înregistrează greutatea corporală și seriile de azi ca să primești sfaturi "
            "reale aici — momentan nu există date."
        )

    phase, week = get_phase(profile)
    if phase == "ramp":
        tips.append(
            (f"You're in the return-to-training ramp (week {week} of 3) after your layoff. "
             f"Weights are intentionally lighter than your old PRs — this protects your "
             f"joints/tendons while your body re-adapts. Full progression resumes after week 3.")
            if not is_ro else
            (f"Ești în faza de revenire la antrenament (săptămâna {week} din 3) după pauză. "
             f"Greutățile sunt intenționat mai mici decât recordurile tale vechi — protejează "
             f"articulațiile/tendoanele cât timp corpul se readaptează. Progresia normală "
             f"reîncepe după săptămâna 3.")
        )

    rate = _weight_trend(weight_log)
    if rate is not None:
        if rate <= -1.2:
            tips.append(
                ("You're losing weight faster than ~1%/week. That risks losing strength/muscle "
                 "along with fat. Consider adding ~150-250 kcal/day.") if not is_ro else
                ("Pierzi în greutate mai repede de ~1%/săptămână. Riști să pierzi forță/mușchi "
                 "odată cu grăsimea. Ia în calcul să adaugi ~150-250 kcal/zi.")
            )
        elif -0.15 <= rate <= 0.15 and len(weight_log) >= 3:
            tips.append(
                ("Weight has been flat for a while — if fat loss is the priority, consider "
                 "reducing ~100-150 kcal/day or adding a short daily walk.") if not is_ro else
                ("Greutatea a stagnat de ceva timp — dacă pierderea de grăsime e prioritatea, "
                 "ia în calcul o reducere de ~100-150 kcal/zi sau o plimbare zilnică scurtă.")
            )
        elif rate < -0.15:
            tips.append(
                (f"Weight trending down at a healthy ~{abs(round(rate,2))}%/week. Good pace for "
                 f"keeping strength while leaning out — keep it up.") if not is_ro else
                (f"Greutatea scade într-un ritm sănătos de ~{abs(round(rate,2))}%/săptămână. "
                 f"Ritm bun pentru a păstra forța cât slăbești — continuă așa.")
            )

    sessions = _sessions_last_7_days(workout_log)
    target_days = int(profile.get("training_days_per_week", 4))
    if workout_log and sessions < target_days:
        tips.append(
            (f"Only {sessions}/{target_days} planned sessions logged in the last 7 days. "
             f"Consistency matters more than any single workout — try to get the next one in.")
            if not is_ro else
            (f"Doar {sessions}/{target_days} antrenamente planificate înregistrate în ultimele "
             f"7 zile. Consistența contează mai mult decât un singur antrenament — încearcă să "
             f"nu ratezi următorul.")
        )

    dropped_lifts = _strength_trend_flags(workout_log)
    if dropped_lifts:
        names = ", ".join(dropped_lifts)
        tips.append(
            (f"Your working weight dropped session-over-session on: {names}. Check sleep, "
             f"protein intake, and whether calories are too low right now.") if not is_ro else
            (f"Greutatea de lucru a scăzut de la o sesiune la alta la: {names}. Verifică somnul, "
             f"aportul de proteine și dacă nu cumva caloriile sunt prea mici acum.")
        )

    return tips
