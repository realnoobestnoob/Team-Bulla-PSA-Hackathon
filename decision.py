import json
import os
import google.generativeai as genai
from .base import extract_json, console, MODEL

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

SYSTEM = """You are the Decision Engine for the Green Port Control Tower.
Synthesise recommendations from Transport, Energy, and Climate agents into a single action plan.

Tagging rules:
- "auto"     → safe to execute immediately (routine dispatch, safe charging delay)
- "escalate" → requires human approval (high weather risk, reefer safety, grid overload)

Output ONLY a JSON array:
[
  {"action": "dispatch",        "details": {"truck_id": "T03", "move_id": "M01"}, "reason": "...", "tag": "auto"},
  {"action": "delay_charging",  "details": {"truck_id": "T10", "delay_mins": 20}, "reason": "...", "tag": "auto"},
  {"action": "delay_move",      "details": {"move_id": "M03"},                    "reason": "...", "tag": "escalate"}
]"""


def run_decision_agent(port_data: dict, transport_recs: list, energy_recs: dict, climate_recs: dict) -> tuple:
    msg = (
        f"Transport recommendations:\n{json.dumps(transport_recs, indent=2)}\n\n"
        f"Energy recommendations:\n{json.dumps(energy_recs, indent=2)}\n\n"
        f"Climate recommendations:\n{json.dumps(climate_recs, indent=2)}\n\n"
        f"Weather: {port_data['weather']} | "
        f"Grid: {port_data['grid_load_kw']}/{port_data['grid_capacity_kw']} kW\n\n"
        "Create the unified action plan."
    )

    model = genai.GenerativeModel(model_name=MODEL, system_instruction=SYSTEM)
    response = model.generate_content(msg)

    plan = extract_json(response.text)
    if not isinstance(plan, list):
        plan = []

    escalated = [a for a in plan if a.get("tag") == "escalate"]
    return plan, escalated
