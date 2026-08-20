import json
from .base import run_agent, extract_json
from tools.emissions import emissions_calculator
from tools.weather import weather_risk_assessor

TOOLS = [
    {
        "name": "emissions_calculator",
        "description": "Calculate CO2 emitted and saved for a truck over a given distance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "truck_id": {"type": "string"},
                "distance_km": {"type": "number"},
            },
            "required": ["truck_id", "distance_km"],
        },
    },
    {
        "name": "weather_risk_assessor",
        "description": "Assess operational risk of a container move in current weather.",
        "input_schema": {
            "type": "object",
            "properties": {
                "move_id": {"type": "string"},
            },
            "required": ["move_id"],
        },
    },
]

SYSTEM = """You are the Climate Agent for the Green Port Control Tower.
Assess emissions impact and weather safety for all planned moves.

Rules:
- Check weather risk for all reefer moves and any medium/high-priority berth moves.
- Calculate CO2 saved for each assigned ePM truck vs diesel baseline.
- Flag any move with risk=high for escalation.

Output ONLY a JSON object:
{
  "total_co2_saved_kg": 3.84,
  "epm_fraction": 0.8,
  "risky_moves": [{"move_id": "M03", "risk": "high", "reason": "...", "escalate": true}],
  "emissions_by_truck": [{"truck_id": "T03", "co2_saved_kg": 0.96}]
}"""


def run_climate_agent(port_data: dict, transport_recs: list) -> dict:
    move_ids = [m["id"] for m in port_data["container_moves"]]
    msg = (
        f"Port state:\n{json.dumps(port_data, indent=2)}\n\n"
        f"Planned truck assignments: {json.dumps(transport_recs, indent=2)}\n\n"
        f"Assess weather risk for all moves: {move_ids}. "
        f"Calculate emissions saved for each assigned truck."
    )
    handlers = {
        "emissions_calculator":  lambda truck_id, distance_km: emissions_calculator(truck_id, distance_km, port_data),
        "weather_risk_assessor": lambda move_id: weather_risk_assessor(move_id, port_data),
    }
    result = extract_json(run_agent("Climate", SYSTEM, msg, TOOLS, handlers))
    return result if isinstance(result, dict) else {"raw": result}
