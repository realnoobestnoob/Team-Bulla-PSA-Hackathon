import json
from .base import run_agent, extract_json
from tools.route import get_vehicle_options, calculate_route
from tools.emissions import estimate_emissions
from tools.energy import check_energy_impact
from tools.weather import check_weather_risk

TOOL_DEFS = [
    {
        "name": "get_vehicle_options",
        "description": "Get ranked list of available vehicles suitable for a job.",
        "input_schema": {
            "type": "object",
            "properties": {"job_id": {"type": "string", "description": "Job ID to assign"}},
            "required": ["job_id"]
        }
    },
    {
        "name": "calculate_route",
        "description": "Calculate distance, travel time, battery usage, and feasibility for a vehicle-job pair.",
        "input_schema": {
            "type": "object",
            "properties": {
                "vehicle_id": {"type": "string"},
                "job_id": {"type": "string"}
            },
            "required": ["vehicle_id", "job_id"]
        }
    },
    {
        "name": "estimate_emissions",
        "description": "Estimate CO2 emitted and saved vs diesel baseline for a vehicle over a distance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "vehicle_id": {"type": "string"},
                "distance_km": {"type": "number"}
            },
            "required": ["vehicle_id", "distance_km"]
        }
    },
    {
        "name": "check_energy_impact",
        "description": "Forecast grid load impact of dispatching a number of electric vehicles.",
        "input_schema": {
            "type": "object",
            "properties": {"electric_dispatches": {"type": "integer"}},
            "required": ["electric_dispatches"]
        }
    },
    {
        "name": "check_weather_risk",
        "description": "Assess operational weather risk for a specific job.",
        "input_schema": {
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"]
        }
    },
]

SYSTEM = """You are the Green Port Control Tower AI.
Your role is to analyse the current port state and propose an operational plan that balances:
- Carbon emissions (prefer electric vehicles)
- Operational efficiency (meet job deadlines)
- Grid energy safety (do not exceed capacity)
- Weather and safety risk

Rules:
- Use tools to gather data before proposing actions. Do not invent numbers.
- Prefer electric vehicles. Only use diesel if no electric option is feasible.
- Never assign a vehicle that is not idle or has insufficient battery/fuel.
- If weather risk is high for a low-priority job, recommend delay.
- High-priority jobs must always be covered if at all possible.
- If replanning due to rejection, respect the stated reason and adjust accordingly.

Output ONLY a JSON array of proposed actions:
[
  {
    "id": "A001",
    "type": "dispatch",
    "parameters": {"vehicle_id": "V01", "job_id": "J01"},
    "reason": "V01 is electric with 87% battery, lowest emissions, meets deadline.",
    "risk": "low",
    "estimated_impact": {"co2_kg": 0, "co2_saved_kg": 4.0, "energy_kwh": 7.5},
    "requires_approval": false
  }
]

Action types: dispatch | delay_job | recharge
Set requires_approval=true for any action involving high safety risk or irreversible change."""


def run_control_tower(port_state: dict, replan_reason: str = "") -> list:
    high_jobs = [jid for jid, j in port_state["jobs"].items()
                 if j.get("status") == "unassigned" and j.get("priority") == "high"]
    all_unassigned = [jid for jid, j in port_state["jobs"].items()
                      if j.get("status") == "unassigned"]

    replan_note = f"\n\nREPLANNING REASON: {replan_reason}" if replan_reason else ""

    msg = (
        f"Current port state:\n{json.dumps(port_state, indent=2)}{replan_note}\n\n"
        f"HIGH priority jobs to cover: {high_jobs}\n"
        f"All unassigned jobs: {all_unassigned}\n\n"
        "Use tools to evaluate options, then produce the action plan."
    )

    handlers = {
        "get_vehicle_options":  lambda job_id: get_vehicle_options(job_id, port_state),
        "calculate_route":      lambda vehicle_id, job_id: calculate_route(vehicle_id, job_id, port_state),
        "estimate_emissions":   lambda vehicle_id, distance_km: estimate_emissions(vehicle_id, distance_km, port_state),
        "check_energy_impact":  lambda electric_dispatches: check_energy_impact(electric_dispatches, port_state),
        "check_weather_risk":   lambda job_id: check_weather_risk(job_id, port_state),
    }

    result = extract_json(run_agent("ControlTower", SYSTEM, msg, TOOL_DEFS, handlers))
    return result if isinstance(result, list) else []
