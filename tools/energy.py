CHARGE_RATE_KW = 150
MOVE_LOAD_KW = 20


def energy_demand_forecast(planned_dispatches: int, port_data: dict) -> dict:
    charging_count = sum(1 for t in port_data["trucks"].values() if t["status"] == "charging")
    base = port_data["grid_load_kw"]
    capacity = port_data["grid_capacity_kw"]

    dispatches_from_chargers = min(planned_dispatches, charging_count)
    projected = base - (dispatches_from_chargers * CHARGE_RATE_KW) + (planned_dispatches * MOVE_LOAD_KW)
    headroom = capacity - projected

    return {
        "current_load_kw": base, "projected_load_kw": round(projected),
        "capacity_kw": capacity, "headroom_kw": round(headroom),
        "safe": headroom > 150, "overload": headroom < 0,
    }


def charging_rescheduler(truck_id: str, delay_mins: int, port_data: dict) -> dict:
    truck = port_data["trucks"].get(truck_id)
    if not truck:
        return {"error": "Truck not found"}
    if truck["status"] != "charging":
        return {"error": f"{truck_id} is not charging"}

    safe = truck["battery_pct"] >= 30
    return {
        "truck_id": truck_id, "current_battery_pct": truck["battery_pct"],
        "delay_mins": delay_mins, "safe_to_delay": safe,
        "reason": "Above 30% minimum threshold" if safe else "Battery too low — do not delay",
        "grid_kw_freed": CHARGE_RATE_KW if safe else 0,
    }
