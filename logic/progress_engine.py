"""
progress_engine.py
-------------------
Turns raw logs (weight, sets, meals, steps) into chart-ready series and a
rule-based weekly summary. All functions take plain lists of dicts (as
returned by routes after querying the DB) and a `period_days` filter, so
they're testable without a database.

The "AI weekly summary" is deterministic and explainable — no LLM call —
built from the same kind of trend checks as the workout coach: PR counts,
volume trend, consistency, calorie/protein adherence.
"""

from datetime import date, timedelta
from collections import defaultdict

from logic.workout_engine import estimate_1rm


def _since(period_days):
    return (date.today() - timedelta(days=period_days)).isoformat()


def weight_series(weight_logs, period_days=90):
    cutoff = _since(period_days)
    rows = sorted([w for w in weight_logs if w["date"] >= cutoff], key=lambda w: w["date"])
    return [{"date": w["date"], "weight_kg": w["weight_kg"]} for w in rows]


def e1rm_series(set_logs, exercise_key, period_days=180):
    cutoff = _since(period_days)
    by_date = defaultdict(float)
    for s in set_logs:
        if s["exercise_key"] != exercise_key or s["date"] < cutoff or s.get("is_warmup"):
            continue
        e1 = estimate_1rm(s.get("weight_kg"), s.get("reps_done"))
        by_date[s["date"]] = max(by_date[s["date"]], e1)
    return [{"date": d, "e1rm": round(v, 1)} for d, v in sorted(by_date.items())]


def volume_series(set_logs, period_days=90, group_by_week=True):
    """Total training volume (kg lifted) over time, optionally bucketed by
    ISO week for a cleaner chart than one point per session."""
    cutoff = _since(period_days)
    buckets = defaultdict(float)
    for s in set_logs:
        if s["date"] < cutoff or s.get("is_warmup"):
            continue
        vol = (s.get("weight_kg") or 0) * (s.get("reps_done") or 0)
        if group_by_week:
            d = date.fromisoformat(s["date"])
            key = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
        else:
            key = s["date"]
        buckets[key] += vol
    return [{"period": k, "volume_kg": round(v)} for k, v in sorted(buckets.items())]


def consistency_series(set_logs, training_days_per_week, period_days=56):
    """Sessions actually logged per ISO week vs. the planned count."""
    cutoff = _since(period_days)
    sessions_by_week = defaultdict(set)
    for s in set_logs:
        if s["date"] < cutoff:
            continue
        d = date.fromisoformat(s["date"])
        key = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
        sessions_by_week[key].add(s["date"])
    return [
        {"period": k, "sessions": len(v), "planned": training_days_per_week}
        for k, v in sorted(sessions_by_week.items())
    ]


def calorie_and_protein_series(meal_entries, protein_target_g, period_days=30):
    cutoff = _since(period_days)
    by_date = defaultdict(lambda: {"kcal": 0, "protein_g": 0.0})
    for e in meal_entries:
        if e["date"] < cutoff:
            continue
        by_date[e["date"]]["kcal"] += e.get("kcal", 0)
        by_date[e["date"]]["protein_g"] += e.get("protein_g", 0) or 0
    series = []
    protein_hit_days = 0
    for d, vals in sorted(by_date.items()):
        hit = vals["protein_g"] >= protein_target_g * 0.9
        protein_hit_days += 1 if hit else 0
        series.append({"date": d, "kcal": round(vals["kcal"]), "protein_g": round(vals["protein_g"], 1),
                        "protein_target_hit": hit})
    return series, protein_hit_days


def step_series(step_logs, period_days=30):
    cutoff = _since(period_days)
    rows = sorted([s for s in step_logs if s["date"] >= cutoff], key=lambda s: s["date"])
    return [{"date": s["date"], "steps": s["steps"]} for s in rows]


def personal_records(set_logs, exercises_by_key, period_days=None):
    """Best e1RM ever logged per exercise (all main lifts with any history)."""
    cutoff = _since(period_days) if period_days else None
    best = {}
    for s in set_logs:
        if cutoff and s["date"] < cutoff:
            continue
        if s.get("is_warmup"):
            continue
        e1 = estimate_1rm(s.get("weight_kg"), s.get("reps_done"))
        key = s["exercise_key"]
        if key not in best or e1 > best[key]["e1rm"]:
            best[key] = {"exercise_key": key, "e1rm": e1, "date": s["date"],
                         "weight_kg": s.get("weight_kg"), "reps_done": s.get("reps_done")}
    out = list(best.values())
    for r in out:
        ex = exercises_by_key.get(r["exercise_key"])
        r["exercise_name_en"] = ex["name_en"] if ex else r["exercise_key"]
        r["exercise_name_ro"] = ex["name_ro"] if ex else r["exercise_key"]
    out.sort(key=lambda r: r["e1rm"], reverse=True)
    return out


def weekly_summary(weight_logs, set_logs, meal_entries, profile_dict, targets, exercises_by_key, lang="en"):
    """Rule-based weekly summary: what improved, what stayed the same,
    what may need adjusting. Mirrors what a coach would glance at."""
    is_ro = lang == "ro"
    lines = []

    w_series = weight_series(weight_logs, period_days=14)
    if len(w_series) >= 2:
        change = w_series[-1]["weight_kg"] - w_series[0]["weight_kg"]
        if abs(change) < 0.2:
            lines.append(("Body weight has been essentially flat over the last two weeks." if not is_ro
                           else "Greutatea corporală a fost aproape constantă în ultimele două săptămâni."))
        else:
            direction_en = "down" if change < 0 else "up"
            direction_ro = "scăzut" if change < 0 else "crescut"
            lines.append((f"Body weight is {direction_en} {abs(round(change,1))}kg over the last two weeks."
                           if not is_ro else
                           f"Greutatea corporală a {direction_ro} cu {abs(round(change,1))}kg în ultimele două săptămâni."))

    prs = personal_records(set_logs, exercises_by_key, period_days=7)
    if prs:
        names = ", ".join(r["exercise_name_ro" if is_ro else "exercise_name_en"] for r in prs[:3])
        lines.append((f"New personal records this week: {names}." if not is_ro
                       else f"Recorduri personale noi săptămâna asta: {names}."))

    consistency = consistency_series(set_logs, profile_dict.get("training_days_per_week", 4), period_days=7)
    if consistency:
        sessions = consistency[-1]["sessions"]
        planned = consistency[-1]["planned"]
        if sessions < planned:
            lines.append((f"Logged {sessions}/{planned} planned sessions this week — consistency matters more than any single workout."
                           if not is_ro else
                           f"Ai înregistrat {sessions}/{planned} antrenamente planificate săptămâna asta — consistența contează mai mult decât un singur antrenament."))
        else:
            lines.append((f"Hit all {planned} planned sessions this week." if not is_ro
                           else f"Ai bifat toate cele {planned} antrenamente planificate săptămâna asta."))

    cal_series, protein_hit_days = calorie_and_protein_series(meal_entries, targets["protein_g"], period_days=7)
    if cal_series:
        avg_kcal = round(sum(d["kcal"] for d in cal_series) / len(cal_series))
        target = targets["target_calories"]
        if avg_kcal < target * 0.85:
            lines.append((f"Average intake (~{avg_kcal} kcal) is noticeably under target (~{target}) — "
                           f"make sure the deficit isn't larger than intended." if not is_ro else
                           f"Consumul mediu (~{avg_kcal} kcal) e vizibil sub țintă (~{target}) — "
                           f"asigură-te că deficitul nu e mai mare decât intenționat."))
        lines.append((f"Hit your protein target on {protein_hit_days}/{len(cal_series)} logged days."
                       if not is_ro else
                       f"Ai atins ținta de proteine în {protein_hit_days}/{len(cal_series)} zile înregistrate."))

    return lines
