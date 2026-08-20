import json
from .base import run_agent, extract_json
from tools.energy import energy_demand_forecast, charging_rescheduler

TOOLS = [
    {
        "name": "energy_demand_forecast",
        "description": "Forecast grid load given number of planned truck dispatches.",
        "input_schema": {
            "type": "object",
            "properties": {
                "planned_dispatches": {"type": "integer", "description": "Number of trucks about to be dispatched"},
            },
            "required": ["planned_dispatches"],
        },
    },
    {
        "name": "charging_rescheduler",
        "description": "Check if a charging truck can safely delay charging to free grid capacity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "truck_id": {"type": "string"},
                "delay_mins": {"type": "integer", "description": "Minutes to delay charging"},
            },
            "required": ["truck_id", "delay_mins"],
        },
    },
]

SYSTEM = """You are the Energy Agent for the Green Port Control Tower.
Ensure grid stays safely below capacity when trucks are dispatched.

Rules:
- Grid must stay below 3000 kW (capacity).
- Only delay charging if truck battery >= 30%.
- Prefer delaying trucks with highest battery first.
- Do not delay T05 (battery 21% — too low).

Call energy_demand_forecast first, then charging_rescheduler if needed.

Output ONLY a JSON object:
{
  "planned_dispatches": 4,
  "grid_safe": true,
  "projected_load_kw": 2430,
  "headroom_kw": 570,
  "charging_delays": [{"truck_id": "T10", "delay_mins": 20, "reason": "..."}]
}"""


def run_energy_agent(port_data: dict) -> dict:
    charging = [tid for tid, t in port_data["trucks"].items() if t["status"] == "charging"]
    msg = (
        f"Port state:\n{json.dumps(port_data, indent=2)}\n\n"
        f"4 trucks are about to be dispatched (high-priority moves). "
        f"Charging trucks: {charging}. Ensure grid safety."
    )
    handlers = {
        "energy_demand_forecast": lambda planned_dispatches: energy_demand_forecast(planned_dispatches, port_data),
        "charging_rescheduler":   lambda truck_id, delay_mins: charging_rescheduler(truck_id, delay_mins, port_data),
    }
    result = extract_json(run_agent("Energy", SYSTEM, msg, TOOLS, handlers))
    return result if isinstance(result, dict) else {"raw": result}
