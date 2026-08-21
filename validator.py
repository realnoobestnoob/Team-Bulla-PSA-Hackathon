"""
Deterministic constraint validator.
AI proposes — code validates — humans decide — code executes.
"""


def validate_action(action: dict, port_state: dict) -> tuple:
    """Returns (is_valid: bool, reason: str)."""
    atype = action.get("type")
    params = action.get("parameters", {})
    obj = port_state["objectives"]["constraints"]

    if atype == "dispatch":
        vid = params.get("vehicle_id")
        jid = params.get("job_id")

        v = port_state["vehicles"].get(vid)
        if not v:
            return False, f"Vehicle {vid} does not exist"
        if v.get("status") in ("dispatched", "breakdown"):
            return False, f"{vid} is not available (status: {v.get('status')})"

        j = port_state["jobs"].get(jid)
        if not j:
            return False, f"Job {jid} does not exist"
        if j.get("status") == "assigned":
            return False, f"{jid} is already assigned"

        if v["type"] == "electric":
            if v.get("battery", 0) < obj["min_battery_reserve_pct"] + 10:
                return False, f"{vid} battery too low ({v.get('battery')}%)"
        else:
            if v.get("fuel", 0) < obj["min_fuel_reserve_pct"] + 10:
                return False, f"{vid} fuel too low ({v.get('fuel')}%)"

        return True, "Valid"

    if atype == "delay_job":
        jid = params.get("job_id")
        j = port_state["jobs"].get(jid)
        if not j:
            return False, f"Job {jid} does not exist"
        if j.get("priority") == "high":
            return False, f"Cannot delay HIGH priority job {jid} without human override"
        return True, "Valid"

    if atype == "recharge":
        vid = params.get("vehicle_id")
        v = port_state["vehicles"].get(vid)
        if not v:
            return False, f"Vehicle {vid} does not exist"
        if v["type"] != "electric":
            return False, f"{vid} is not electric — cannot recharge"
        return True, "Valid"

    return False, f"Unknown action type: {atype}"


def validate_all(actions: list, port_state: dict) -> list:
    """Validate a list of proposed actions. Returns list with validation results added."""
    results = []
    # Track tentatively assigned vehicles/jobs to avoid double-assignment
    assigned_vehicles = set()
    assigned_jobs = set()

    for a in actions:
        params = a.get("parameters", {})
        vid = params.get("vehicle_id")
        jid = params.get("job_id")

        if vid and vid in assigned_vehicles:
            results.append({**a, "valid": False, "validation_reason": f"{vid} already assigned in this plan"})
            continue
        if jid and jid in assigned_jobs:
            results.append({**a, "valid": False, "validation_reason": f"{jid} already assigned in this plan"})
            continue

        ok, reason = validate_action(a, port_state)
        results.append({**a, "valid": ok, "validation_reason": reason})

        if ok and a.get("type") == "dispatch":
            if vid: assigned_vehicles.add(vid)
            if jid: assigned_jobs.add(jid)

    return results
