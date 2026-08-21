RISK = {"clear":"low","cloudy":"low","light_rain":"medium","heavy_rain":"high","storm":"critical"}


def check_weather_risk(job_id: str, port_state: dict) -> dict:
    job = port_state["jobs"].get(job_id)
    if not job:
        return {"error": f"Job {job_id} not found"}

    weather = port_state["weather"]
    cond = weather.get("condition","clear")
    wind = weather.get("wind_speed", 0)
    risk = RISK.get(cond, "low")

    if wind > 40:
        risk = "high"
        reason = f"Wind speed {wind} km/h exceeds safe operating threshold"
    elif risk == "high":
        reason = f"Heavy rain — reduced visibility and slippery surfaces"
    elif risk == "medium":
        reason = f"Light rain — monitor conditions"
    else:
        reason = "Conditions acceptable"

    escalate = risk in ("high","critical") and job.get("priority") != "high"
    recommend_delay = risk in ("high","critical") and job.get("priority") == "low"

    return {
        "job_id": job_id, "condition": cond,
        "wind_speed_kmh": wind, "risk": risk,
        "reason": reason, "recommend_delay": recommend_delay,
        "escalate_to_human": escalate,
    }
