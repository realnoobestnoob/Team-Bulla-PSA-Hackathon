DISTANCES = {
    ("A","B"):2.0,("A","C"):3.5,("A","D"):5.0,
    ("B","C"):2.5,("B","D"):3.5,("C","D"):2.0,
}


def _dist(o: str, d: str) -> float:
    return DISTANCES.get((o,d)) or DISTANCES.get((d,o)) or 2.0


def get_vehicle_options(job_id: str, port_state: dict) -> dict:
    job = port_state["jobs"].get(job_id)
    if not job:
        return {"error": f"Job {job_id} not found"}

    obj = port_state["objectives"]["constraints"]
    candidates = []
    for vid, v in port_state["vehicles"].items():
        if v.get("status") != "idle":
            continue
        score = 0
        if v["type"] == "electric" and obj.get("prefer_electric"):
            score += 50
            if v.get("battery",0) >= obj["min_battery_reserve_pct"] + 10:
                score += v.get("battery", 0)
            else:
                continue  # battery too low
        else:
            if v.get("fuel", 0) < obj["min_fuel_reserve_pct"] + 10:
                continue
            score += v.get("fuel", 0) * 0.5

        # Closer is better
        dist_to_origin = _dist(v["location"], job["origin"])
        score -= dist_to_origin * 5
        candidates.append({
            "vehicle_id": vid, "type": v["type"],
            "battery_or_fuel": v.get("battery") or v.get("fuel"),
            "location": v["location"], "score": round(score, 1)
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return {"job_id": job_id, "ranked_vehicles": candidates[:4], "available_count": len(candidates)}


def calculate_route(vehicle_id: str, job_id: str, port_state: dict) -> dict:
    v = port_state["vehicles"].get(vehicle_id)
    j = port_state["jobs"].get(job_id)
    if not v or not j:
        return {"error": "Vehicle or job not found"}

    dist = _dist(j["origin"], j["destination"])
    deadhead = _dist(v["location"], j["origin"]) if v["location"] != j["origin"] else 0
    total = round(dist + deadhead, 2)

    weather = port_state["weather"].get("condition","clear")
    speed = 20 if weather in ("heavy_rain","storm") else 30
    time_mins = round((total / speed) * 60)

    battery_used = round(total * 2.5, 1) if v["type"] == "electric" else 0
    feasible = (
        v.get("battery", 100) >= battery_used + port_state["objectives"]["constraints"]["min_battery_reserve_pct"]
        if v["type"] == "electric"
        else v.get("fuel", 100) >= port_state["objectives"]["constraints"]["min_fuel_reserve_pct"] + 5
    )

    return {
        "vehicle_id": vehicle_id, "job_id": job_id,
        "job_distance_km": dist, "deadhead_km": round(deadhead, 2),
        "total_km": total, "time_mins": time_mins,
        "battery_pct_used": battery_used, "feasible": feasible,
    }
