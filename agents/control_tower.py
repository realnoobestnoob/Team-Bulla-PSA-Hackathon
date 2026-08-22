"""
Green Port Control Tower — single AI planner agent.
Changes from v1:
  - Compressed port-state summary (≈80% fewer prompt tokens)
  - scan_job_fleet batch tool (replaces 5-10 per-job tool calls with 1)
  - Structured reasoning prompt (chain-of-thought, explicit decision order)
  - on_step callback pass-through to Streamlit
"""
import json
from .base import run_agent, extract_json
from tools.route import get_vehicle_options, calculate_route
from tools.emissions import estimate_emissions
from tools.energy import check_energy_impact
from tools.weather import check_weather_risk

# ── Tool definitions ──────────────────────────────────────────────────────────

TOOL_DEFS = [
    {
        "name": "scan_job_fleet",
        "description": (
            "PRIMARY PLANNING TOOL — call this FIRST with all unassigned job IDs. "
            "Returns best vehicle, route feasibility, CO₂ estimate, and weather risk for every job in one shot. "
            "Eliminates the need to call get_vehicle_options + calculate_route + check_weather_risk separately."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "job_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "All unassigned job IDs to evaluate in one batch.",
                }
            },
            "required": ["job_ids"],
        },
    },
    {
        "name": "check_energy_impact",
        "description": "Forecast grid load after dispatching N electric vehicles simultaneously. Call when planning ≥3 EV dispatches.",
        "input_schema": {
            "type": "object",
            "properties": {"electric_dispatches": {"type": "integer", "description": "Number of EVs to dispatch"}},
            "required": ["electric_dispatches"],
        },
    },
    {
        "name": "get_vehicle_options",
        "description": "Get ranked vehicles for a single job. Use only when scan_job_fleet's top pick needs a verified alternative.",
        "input_schema": {
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
        },
    },
    {
        "name": "calculate_route",
        "description": "Calculate exact route metrics for a specific vehicle-job pair. Use to verify a specific edge case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "vehicle_id": {"type": "string"},
                "job_id":     {"type": "string"},
            },
            "required": ["vehicle_id", "job_id"],
        },
    },
]

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM = """You are the Green Port Control Tower AI for PSA Singapore.
Your mission: propose an optimal action plan that maximises sustainability while meeting job deadlines and grid constraints.

## Decision Workflow (follow this order)
1. Call scan_job_fleet with ALL unassigned job IDs to get a complete picture in one shot.
2. Sort jobs by priority: HIGH → MEDIUM → LOW. High-priority jobs MUST be covered if feasible.
3. For each job, assign the best feasible vehicle from scan results (prefer electric, check feasible=true).
4. If dispatching ≥3 electric vehicles, call check_energy_impact to verify grid stays safe.
5. If weather_risk=high AND job priority=low: use delay_job instead of dispatch.
6. If replanning, honour the supervisor's stated constraint FIRST, then optimise the rest.

## Hard Rules
- Never assign a vehicle that is breakdown, dispatched, or has battery <30% / fuel <25%.
- Never double-assign the same vehicle or job within one plan.
- Set requires_approval=true for any high-risk or irreversible action.

## Output — respond with ONLY a valid JSON array, no preamble, no trailing text:
[
  {
    "id": "A001",
    "type": "dispatch",
    "parameters": {"vehicle_id": "V01", "job_id": "J01"},
    "reason": "Specific reason: V01 electric 87% battery at A, J01 needs A→D (5km), 0 CO₂ emitted vs 4.0 kg diesel.",
    "risk": "low",
    "estimated_impact": {"co2_kg": 0, "co2_saved_kg": 4.0, "energy_kwh": 7.5},
    "requires_approval": false
  }
]
Valid action types: dispatch | delay_job | recharge"""


# ── State compressor ──────────────────────────────────────────────────────────

def _summarize_port_state(port_state: dict) -> str:
    """
    Compact representation of port state — ~80% fewer tokens than full JSON dump.
    Preserves all decision-relevant data.
    """
    vehicles = port_state["vehicles"]
    jobs     = port_state["jobs"]
    weather  = port_state["weather"]
    energy   = port_state["energy"]
    c        = port_state["objectives"]["constraints"]

    lines = [f"TIME: {port_state.get('time', '?')}"]

    # Vehicles: one line per powertrain, ✓=usable ✗=too low/unavailable
    def ev_str(vid, v):
        bat = v.get("battery", 0)
        ok  = "✓" if bat >= 30 and v.get("status") == "idle" else "✗"
        return f"{vid}({v.get('location','?')},{bat}%{ok})"

    def dv_str(vid, v):
        fuel = v.get("fuel", 0)
        ok   = "✓" if fuel >= 25 and v.get("status") == "idle" else "✗"
        return f"{vid}({v.get('location','?')},{fuel}%{ok})"

    ev = [(vid, v) for vid, v in vehicles.items() if v["type"] == "electric"]
    dv = [(vid, v) for vid, v in vehicles.items() if v["type"] == "diesel"]
    lines.append("ELECTRIC: " + " ".join(ev_str(vid, v) for vid, v in ev))
    lines.append("DIESEL:   " + " ".join(dv_str(vid, v) for vid, v in dv))

    not_idle = {vid: v["status"] for vid, v in vehicles.items() if v["status"] != "idle"}
    if not_idle:
        lines.append("OFFLINE:  " + "  ".join(f"{vid}={s}" for vid, s in not_idle.items()))

    # Jobs: grouped by priority, unassigned only
    for prio in ("high", "medium", "low"):
        jlist = [(jid, j) for jid, j in jobs.items()
                 if j.get("priority") == prio and j.get("status") == "unassigned"]
        if jlist:
            lines.append(
                f"JOBS_{prio.upper()}: " +
                " ".join(f"{jid}({j['origin']}→{j['destination']},{j['deadline']})" for jid, j in jlist)
            )

    # Environment
    grid_pct = round(energy["grid_load_kw"] / energy["grid_capacity_kw"] * 100)
    lines.append(f"WEATHER:  {weather.get('condition','?')} | wind={weather.get('wind_speed','?')}km/h")
    lines.append(
        f"ENERGY:   {energy['grid_load_kw']}/{energy['grid_capacity_kw']}kW ({grid_pct}%) "
        f"| renewable={round(energy.get('renewable_fraction', 0)*100)}%"
    )
    lines.append(
        f"RULES:    prefer_electric={c['prefer_electric']} "
        f"| bat_reserve≥{c['min_battery_reserve_pct']}% "
        f"| fuel_reserve≥{c['min_fuel_reserve_pct']}%"
    )
    return "\n".join(lines)


# ── Batch tool implementation ─────────────────────────────────────────────────

def _scan_job_fleet(job_ids: list, port_state: dict) -> dict:
    """
    Best vehicle + route + emissions + weather for every job in one call.
    Replaces N×(get_vehicle_options + calculate_route + estimate_emissions + check_weather_risk).
    """
    results = {}
    for jid in list(job_ids):      # list() handles proto RepeatedScalarContainer
        options = get_vehicle_options(jid, port_state)
        ranked  = options.get("ranked_vehicles", [])

        if not ranked:
            results[jid] = {
                "best_vehicle": None,
                "feasible": False,
                "reason": "No eligible vehicles — all busy, broken, or below reserve.",
            }
            continue

        best  = ranked[0]
        vid   = best["vehicle_id"]
        route = calculate_route(vid, jid, port_state)
        em    = estimate_emissions(vid, route.get("total_km", 2.0), port_state)
        wx    = check_weather_risk(jid, port_state)

        results[jid] = {
            "best_vehicle":    vid,
            "vehicle_type":    best["type"],
            "vehicle_level":   best["battery_or_fuel"],
            "feasible":        route.get("feasible", False),
            "total_km":        route.get("total_km"),
            "time_mins":       route.get("time_mins"),
            "co2_emitted_kg":  em.get("co2_emitted_kg", 0),
            "co2_saved_kg":    em.get("co2_saved_vs_diesel_kg", 0),
            "energy_kwh":      round(route.get("total_km", 0) * 1.5, 1) if best["type"] == "electric" else 0,
            "weather_risk":    wx.get("risk", "low"),
            "recommend_delay": wx.get("recommend_delay", False),
            "alternatives":    len(ranked) - 1,   # how many fallback vehicles exist
        }
    return results


# ── Public entry point ────────────────────────────────────────────────────────

def run_control_tower(
    port_state:    dict,
    replan_reason: str = "",
    on_step=None,          # optional callback(str) for Streamlit live log
) -> list:
    unassigned  = [jid for jid, j in port_state["jobs"].items() if j.get("status") == "unassigned"]
    high_jobs   = [jid for jid in unassigned
                   if port_state["jobs"][jid].get("priority") == "high"]

    replan_note = (
        f"\n\n⚠ REPLANNING — Supervisor constraint: \"{replan_reason}\"\n"
        f"Honour this constraint first, then optimise the remaining assignments."
        if replan_reason else ""
    )

    user_msg = (
        f"{_summarize_port_state(port_state)}{replan_note}\n\n"
        f"HIGH-priority jobs that must be covered: {high_jobs}\n"
        f"All unassigned job IDs: {unassigned}\n\n"
        f"Start by calling scan_job_fleet with: {unassigned}"
    )

    handlers = {
        "scan_job_fleet":      lambda job_ids: _scan_job_fleet(job_ids, port_state),
        "check_energy_impact": lambda electric_dispatches: check_energy_impact(electric_dispatches, port_state),
        "get_vehicle_options": lambda job_id: get_vehicle_options(job_id, port_state),
        "calculate_route":     lambda vehicle_id, job_id: calculate_route(vehicle_id, job_id, port_state),
    }

    raw    = run_agent("ControlTower", SYSTEM, user_msg, TOOL_DEFS, handlers, on_step=on_step)
    result = extract_json(raw)
    return result if isinstance(result, list) else []
