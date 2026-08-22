"""
KPI scoring for Green Port Control Tower.
Evaluates each run across four dimensions: emissions, job coverage, grid safety, plan quality.
Score: 0–100  |  Grade: A+/A/B/C/D/F
"""

WEIGHTS = {
    "emissions": 40,  # CO2 saved vs all-diesel baseline
    "coverage":  30,  # dispatched jobs / total actionable
    "grid":      20,  # grid headroom vs capacity
    "quality":   10,  # validation pass rate (AI plan accuracy)
}
REPLAN_PENALTY = 5    # points deducted per supervisor-requested replan


def compute_run_score(
    baseline:          dict,
    projected:         dict,
    validated_actions: list,
    executed_actions:  list,
    replan_count:      int  = 0,
    token_usage:       dict = None,
) -> dict:
    """
    Return score dict with total (0-100), letter grade, per-category breakdown,
    and token efficiency label.
    """
    token_usage = token_usage or {}

    # ── Emissions (0–40) ──────────────────────────────────────────────────────
    baseline_co2 = max(baseline.get("co2_kg", 0), 0.01)   # avoid ÷0
    co2_saved    = max(projected.get("co2_saved_kg", 0), 0)
    emissions_score = min(WEIGHTS["emissions"], (co2_saved / baseline_co2) * WEIGHTS["emissions"])

    # ── Coverage (0–30) ───────────────────────────────────────────────────────
    total_jobs   = max(baseline.get("jobs_covered", 1), 1)
    dispatched   = sum(1 for a in executed_actions if a.get("type") == "dispatch")
    coverage_score = (dispatched / total_jobs) * WEIGHTS["coverage"]

    # ── Grid Safety (0–20) ────────────────────────────────────────────────────
    if projected.get("grid_safe", True):
        proj_kw  = projected.get("projected_grid_kw", 0)
        cap_kw   = 3000  # from energy.json — adjust if data changes
        headroom = max(cap_kw - proj_kw, 0) / cap_kw
        grid_score = headroom * WEIGHTS["grid"]
    else:
        grid_score = 0.0   # overloaded grid = zero marks

    # ── Plan Quality (0–10) ───────────────────────────────────────────────────
    total_proposed = max(len(validated_actions), 1)
    valid_count    = sum(1 for a in validated_actions if a.get("valid"))
    quality_score  = (valid_count / total_proposed) * WEIGHTS["quality"]

    # ── Replan penalty ────────────────────────────────────────────────────────
    penalty = replan_count * REPLAN_PENALTY

    # ── Final ─────────────────────────────────────────────────────────────────
    raw   = emissions_score + coverage_score + grid_score + quality_score - penalty
    total = max(0.0, min(100.0, round(raw, 1)))

    # ── Token efficiency (informational) ──────────────────────────────────────
    n_tokens = token_usage.get("total_tokens", 0)
    token_efficiency = (
        "Excellent" if n_tokens < 2_000  else
        "Good"      if n_tokens < 5_000  else
        "Fair"      if n_tokens < 10_000 else
        "High"
    )

    return {
        "total_score":      total,
        "grade":            _letter_grade(total),
        "breakdown": {
            "Emissions Saved": round(emissions_score, 1),
            "Job Coverage":    round(coverage_score, 1),
            "Grid Safety":     round(grid_score, 1),
            "Plan Quality":    round(quality_score, 1),
            "Replan Penalty":  round(-penalty, 1),
        },
        "details": {
            "co2_saved_kg":    co2_saved,
            "baseline_co2_kg": baseline.get("co2_kg", 0),
            "jobs_dispatched": dispatched,
            "jobs_total":      total_jobs,
            "grid_safe":       projected.get("grid_safe", True),
            "valid_actions":   valid_count,
            "total_proposed":  total_proposed,
            "replan_count":    replan_count,
        },
        "token_usage":       token_usage,
        "token_efficiency":  token_efficiency,
    }


def _letter_grade(score: float) -> str:
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 70: return "B"
    if score >= 60: return "C"
    if score >= 50: return "D"
    return "F"
