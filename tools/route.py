DISTANCES = {
    ("berth_1", "yard_a"): 1.2, ("berth_1", "yard_b"): 0.8, ("berth_1", "yard_c"): 1.5,
    ("berth_2", "yard_a"): 0.9, ("berth_2", "yard_b"): 1.1, ("berth_2", "yard_c"): 0.7,
    ("yard_a",  "gate_a"): 0.6, ("yard_a",  "gate_b"): 0.9,
    ("yard_b",  "gate_a"): 0.4, ("yard_b",  "gate_b"): 0.7,
    ("yard_c",  "gate_a"): 1.0, ("yard_c",  "gate_b"): 0.5,
}


def _dist(a: str, b: str) -> float:
    a, b = a.lower(), b.lower()
    return DISTANCES.get((a, b)) or DISTANCES.get((b, a)) or 1.0


def route_calculator(move_id: str, truck_id: str, port_data: dict) -> dict:
    move = next((m for m in port_data["container_moves"] if m["id"] == move_id), None)
    truck = port_data["trucks"].get(truck_id)
    if not move or not truck:
        return {"error": "Move or truck not found"}

    dist = _dist(move["origin"], move["dest"])
    empty_leg = truck["location"].lower() not in [move["origin"].lower(), move["dest"].lower()]
    total_km = round(dist + (0.4 if empty_leg else 0), 2)
    speed_kmh = 15 if port_data.get("weather") == "heavy_rain" else 20
    time_mins = round((total_km / speed_kmh) * 60)
    battery_used = round(total_km * 2.5, 1)
    feasible = truck.get("battery_pct", 0) >= battery_used + 15

    return {
        "move_id": move_id, "truck_id": truck_id,
        "distance_km": total_km, "time_mins": time_mins,
        "empty_leg": empty_leg, "battery_pct_used": battery_used, "feasible": feasible,
    }


def assign_truck(move_id: str, prefer_electric: bool, port_data: dict) -> dict:
    move = next((m for m in port_data["container_moves"] if m["id"] == move_id), None)
    if not move:
        return {"error": "Move not found"}

    candidates = []
    for tid, t in port_data["trucks"].items():
        if t["status"] != "idle":
            continue
        score = (50 if prefer_electric and t["type"] == "ePM" else 0)
        score += t.get("battery_pct", 0)
        score -= _dist(t["location"], move["origin"]) * 10
        candidates.append({"truck_id": tid, "score": round(score, 1),
                            "battery_pct": t.get("battery_pct", 0), "type": t["type"]})

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return {"move_id": move_id, "ranked_trucks": candidates[:3], "idle_count": len(candidates)}
