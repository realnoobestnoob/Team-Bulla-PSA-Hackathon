RISK_MAP = {
    "clear": "low", "cloudy": "low",
    "light_rain": "medium", "heavy_rain": "high", "storm": "critical",
}


def weather_risk_assessor(move_id: str, port_data: dict) -> dict:
    move = next((m for m in port_data["container_moves"] if m["id"] == move_id), None)
    if not move:
        return {"error": "Move not found"}

    weather = port_data.get("weather", "clear")
    base_risk = RISK_MAP.get(weather, "low")
    is_reefer = move.get("reefer", False)
    priority = move.get("priority", "low")

    if is_reefer and base_risk == "high":
        risk, reason, escalate = "high", "Reefer container in heavy rain — electrical connection risk", True
    elif base_risk == "high" and priority == "low":
        risk, reason, escalate = "medium", "Low-priority move in heavy rain — recommend delay", False
    else:
        risk, reason, escalate = base_risk, f"{weather.replace('_', ' ').title()} conditions", False

    return {
        "move_id": move_id, "weather": weather,
        "risk": risk, "reason": reason,
        "recommend_delay": risk in ("high", "medium") and priority != "high",
        "escalate": escalate,
    }
