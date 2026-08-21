"""
Loads separate JSON source files and merges them into a single runtime port_state dict.
JSON files = starting environment. port_state = current environment.
"""
import json
import copy
from pathlib import Path

DATA = Path("data")


def load_port_state(scenario: str = "heavy_rain") -> dict:
    vehicles   = json.loads((DATA / "vehicles.json").read_text())
    jobs       = json.loads((DATA / "jobs.json").read_text())
    weather    = json.loads((DATA / "weather.json").read_text())
    equipment  = json.loads((DATA / "equipment.json").read_text())
    charging   = json.loads((DATA / "charging_stations.json").read_text())
    energy     = json.loads((DATA / "energy.json").read_text())
    objectives = json.loads((DATA / "objectives.json").read_text())

    # Index by ID for fast lookup
    state = {
        "time": "09:00",
        "vehicles":          {v["id"]: copy.deepcopy(v) for v in vehicles},
        "jobs":              {j["id"]: copy.deepcopy(j) for j in jobs},
        "equipment":         copy.deepcopy(equipment),
        "charging_stations": {cs["id"]: copy.deepcopy(cs) for cs in charging},
        "weather":           copy.deepcopy(weather),
        "energy":            copy.deepcopy(energy),
        "objectives":        copy.deepcopy(objectives),
    }

    # Apply scenario overrides
    scenario_path = DATA / "scenarios" / f"{scenario}.json"
    if scenario_path.exists():
        overrides = json.loads(scenario_path.read_text()).get("overrides", {})
        if "weather" in overrides:
            state["weather"].update(overrides["weather"])
        if "vehicles" in overrides:
            for vid, changes in overrides["vehicles"].items():
                if vid in state["vehicles"]:
                    state["vehicles"][vid].update(changes)

    return state
