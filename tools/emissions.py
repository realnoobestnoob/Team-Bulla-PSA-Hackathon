DIESEL_CO2_KG_PER_KM = 0.8


def emissions_calculator(truck_id: str, distance_km: float, port_data: dict) -> dict:
    truck = port_data["trucks"].get(truck_id)
    if not truck:
        return {"error": "Truck not found"}

    if truck["type"] == "ePM":
        emitted = 0.0
        saved = round(distance_km * DIESEL_CO2_KG_PER_KM, 2)
    else:
        emitted = round(distance_km * DIESEL_CO2_KG_PER_KM, 2)
        saved = 0.0

    return {
        "truck_id": truck_id, "type": truck["type"],
        "distance_km": distance_km,
        "co2_emitted_kg": emitted, "co2_saved_kg": saved,
    }
