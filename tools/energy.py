def check_energy_impact(electric_dispatches: int, port_state: dict) -> dict:
    energy = port_state["energy"]
    vehicles = port_state["vehicles"]

    charging_count = sum(1 for v in vehicles.values() if v.get("status") == "charging")
    charge_freed = min(electric_dispatches, charging_count) * energy["charge_rate_kw"]
    move_added = electric_dispatches * energy["vehicle_move_load_kw"]

    projected = energy["grid_load_kw"] - charge_freed + move_added
    headroom = energy["grid_capacity_kw"] - projected

    return {
        "current_grid_kw": energy["grid_load_kw"],
        "projected_grid_kw": round(projected),
        "capacity_kw": energy["grid_capacity_kw"],
        "headroom_kw": round(headroom),
        "safe": headroom > 100,
        "overload": headroom < 0,
    }
