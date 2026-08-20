import json
from .base import run_agent, extract_json
from tools.route import route_calculator, assign_truck

TOOLS = [
    {
        "name": "assign_truck",
        "description": "Get ranked idle trucks for a move, preferring ePM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "move_id": {"type": "string", "description": "Container move ID"},
                "prefer_electric": {"type": "boolean", "description": "Prefer ePM trucks"},
            },
            "required": ["move_id", "prefer_electric"],
        },
    },
    {
        "name": "route_calculator",
        "description": "Calculate distance, time, battery usage and feasibility for a truck-move pair.",
        "input_schema": {
            "type": "object",
            "properties": {
                "move_id": {"type": "string"},
                "truck_id": {"type": "string"},
            },
            "required": ["move_id", "truck_id"],
        },
    },
]

SYSTEM = """You are the Transport Agent for the Green Port Control Tower.
Assign the best idle trucks to HIGH priority container moves.

Rules:
- Always prefer ePM (electric) trucks over diesel.
- Never assign a truck with less than 15% battery after the move.
- Minimise empty legs (truck not at move origin).
- Each truck can only be assigned once.

Call assign_truck to get candidates, then route_calculator to confirm feasibility.

Output ONLY a JSON array:
[{"move_id": "M01", "truck_id": "T03", "distance_km": 1.2, "reason": "..."}]"""


def run_transport_agent(port_data: dict) -> list:
    high = [m["id"] for m in port_data["container_moves"] if m["priority"] == "high"]
    msg = (
        f"Port state:\n{json.dumps(port_data, indent=2)}\n\n"
        f"Assign trucks to these HIGH priority moves: {high}"
    )
    handlers = {
        "assign_truck":     lambda move_id, prefer_electric: assign_truck(move_id, prefer_electric, port_data),
        "route_calculator": lambda move_id, truck_id: route_calculator(move_id, truck_id, port_data),
    }
    return extract_json(run_agent("Transport", SYSTEM, msg, TOOLS, handlers))
