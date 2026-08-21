"""
Deterministic impact evaluator.
Compares proposed plan against an all-diesel baseline.
"""

DIESEL_CO2_KG_PER_KM = 0.8
DISTANCES = {
    ("A","B"):2.0,("A","C"):3.5,("A","D"):5.0,
    ("B","C"):2.5,("B","D"):3.5,("C","D"):2.0,
}


def _dist(o: str, d: str) -> float:
    return DISTANCES.get((o,d)) or DISTANCES.get((d,o)) or 2.0


def compute_baseline(port_state: dict) -> dict:
    """Baseline: all unassigned HIGH+MEDIUM jobs done by diesel."""
    jobs = [j for j in port_state["jobs"].values()
            if j.get("status") == "unassigned" and j.get("priority") in ("high","medium")]
    total_km = sum(_dist(j["origin"], j["destination"]) for j in jobs)
    return {
        "jobs_covered": len(jobs),
        "total_km": round(total_km, 2),
        "co2_kg": round(total_km * DIESEL_CO2_KG_PER_KM, 2),
        "energy_kwh": 0,  # diesel baseline uses no grid energy
        "delayed_jobs": 0,
    }


def compute_projected(actions: list, port_state: dict) -> dict:
    """Projected: based on validated proposed actions."""
    vehicles = port_state["vehicles"]
    jobs = port_state["jobs"]
    energy = port_state["energy"]

    co2, kwh, electric_dispatches, covered, delayed = 0.0, 0.0, 0, 0, 0

    for a in actions:
        if not a.get("valid", True):
            continue
        if a["type"] == "dispatch":
            vid = a["parameters"].get("vehicle_id")
            jid = a["parameters"].get("job_id")
            v = vehicles.get(vid, {})
            j = jobs.get(jid, {})
            if not v or not j:
                continue
            dist = _dist(j.get("origin","A"), j.get("destination","B"))
            if v.get("type") == "electric":
                kwh += dist * 1.5          # ~1.5 kWh/km for ePM
                electric_dispatches += 1
            else:
                co2 += dist * DIESEL_CO2_KG_PER_KM
            covered += 1
        elif a["type"] == "delay_job":
            delayed += 1

    # Grid load delta
    charge_freed = min(electric_dispatches, sum(
        1 for v in vehicles.values() if v.get("status") == "charging"
    )) * energy.get("charge_rate_kw", 150)
    move_added = electric_dispatches * energy.get("vehicle_move_load_kw", 20)
    projected_grid = energy["grid_load_kw"] - charge_freed + move_added

    return {
        "jobs_covered": covered,
        "co2_kg": round(co2, 2),
        "co2_saved_kg": round(covered * 2.0 * DIESEL_CO2_KG_PER_KM - co2, 2),
        "energy_kwh": round(kwh, 2),
        "projected_grid_kw": round(projected_grid),
        "grid_safe": projected_grid < port_state["energy"]["grid_capacity_kw"],
        "delayed_jobs": delayed,
    }
