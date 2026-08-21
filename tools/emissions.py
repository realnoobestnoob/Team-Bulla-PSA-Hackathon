DIESEL_CO2_KG_PER_KM = 0.8


def estimate_emissions(vehicle_id: str, distance_km: float, port_state: dict) -> dict:
    v = port_state["vehicles"].get(vehicle_id)
    if not v:
        return {"error": f"Vehicle {vehicle_id} not found"}

    if v["type"] == "electric":
        emitted = 0.0
        saved = round(distance_km * DIESEL_CO2_KG_PER_KM, 2)
    else:
        emitted = round(distance_km * DIESEL_CO2_KG_PER_KM, 2)
        saved = 0.0

    return {
        "vehicle_id": vehicle_id, "type": v["type"],
        "distance_km": distance_km,
        "co2_emitted_kg": emitted,
        "co2_saved_vs_diesel_kg": saved,
    }
