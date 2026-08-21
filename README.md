- Decision making use ai agents
- 

**To do: edit project to use google ai studio (free) instead of anthropic api (not free) but run into some issues!!! Bug appears after using google api**

# 🏗️ Green Port Control Tower

A multi-agent AI system that coordinates sustainability decisions across a simulated PSA port — balancing transport, energy, and climate trade-offs in real time.

Built for **PSA Code Sprint 2.0**.

---

## What it does

You feed in an operational scenario (trucks, container moves, weather, grid load). Four AI agents reason through it in sequence, then produce a prioritised action plan. High-risk decisions pause for a human supervisor to approve or reject before anything executes.

```
Scenario (JSON)
      │
      ▼
 Transport Agent  →  assigns electric trucks to high-priority container moves
      │
 Energy Agent     →  checks grid load, delays charging if headroom is tight
      │
 Climate Agent    →  calculates CO₂ savings, flags reefer moves in bad weather
      │
 Decision Engine  →  merges all recommendations into one action plan
      │
 Human Approval   →  supervisor approves or rejects any escalated actions
      │
 Final Action Log + Impact Summary
```

---

## Requirements

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

---

## Setup

**1. Clone or unzip the project**
```bash
cd green_port_agent
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Add your API key**
```bash
cp .env.example .env
```
Open `.env` and replace `your_key_here` with your actual Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-...
```

**4. Run the demo**
```bash
python run_demo.py
```

---

## What you'll see

The demo runs a pre-loaded scenario: **10 trucks, 10 container moves, 2 cranes down, heavy rain, grid at 80% capacity**.

```
📋 SCENARIO
   Time: 14:00 → 18:00  |  Weather: Heavy Rain  |  Grid: 2400/3000 kW
   10 trucks (7 ePM)  |  2 cranes down  |  10 moves (4 HIGH priority)

── [1/4] TRANSPORT AGENT ──────────────────────
    → [Transport] assign_truck({'move_id': 'M01', 'prefer_electric': True})
    → [Transport] route_calculator({'move_id': 'M01', 'truck_id': 'T03'})
    ...

── [2/4] ENERGY AGENT ─────────────────────────
    → [Energy] energy_demand_forecast({'planned_dispatches': 4})
    → [Energy] charging_rescheduler({'truck_id': 'T10', 'delay_mins': 20})
    ...

── [3/4] CLIMATE AGENT ────────────────────────
    → [Climate] weather_risk_assessor({'move_id': 'M03'})
    → [Climate] emissions_calculator({'truck_id': 'T03', 'distance_km': 1.6})
    ...

── [4/4] DECISION ENGINE ──────────────────────
   Action plan generated.

⚠  HUMAN APPROVAL REQUIRED
   Action: DELAY_MOVE  {'move_id': 'M03'}
   Reason: Reefer container in heavy rain — electrical connection risk
   Approve? [y/n]:
```

After you respond to any escalations, the final action table prints with CO₂ saved, grid headroom, and a count of auto vs human-approved actions.

---

## Project structure

```
green_port_agent/
├── run_demo.py          # entry point — run this
├── graph.py             # LangGraph orchestration
├── state.py             # shared state schema (PortState)
├── approval.py          # human-in-the-loop node
├── data/
│   └── port_state.json  # mock scenario (edit this to change the demo)
├── tools/
│   ├── route.py         # route_calculator, assign_truck
│   ├── emissions.py     # emissions_calculator
│   ├── energy.py        # energy_demand_forecast, charging_rescheduler
│   └── weather.py       # weather_risk_assessor
├── agents/
│   ├── base.py          # shared tool-calling loop
│   ├── transport.py
│   ├── energy.py
│   ├── climate.py
│   └── decision.py
├── requirements.txt
└── .env.example
```

---

## Customising the scenario

Edit `data/port_state.json` to change the demo. Key fields:

| Field | What it controls |
|-------|-----------------|
| `weather` | `"clear"` / `"light_rain"` / `"heavy_rain"` / `"storm"` |
| `grid_load_kw` | Current grid consumption (capacity is 3000 kW) |
| `trucks[*].status` | `"idle"` / `"charging"` / `"dispatched"` |
| `trucks[*].battery_pct` | Battery level — agents won't assign trucks below 15% after a move |
| `container_moves[*].priority` | `"high"` / `"medium"` / `"low"` |
| `container_moves[*].reefer` | `true` triggers escalation in bad weather |

---

## Tech stack

| Component | Purpose |
|-----------|---------|
| Claude API (`claude-sonnet-4-6`) | Reasoning and decision-making inside each agent |
| LangGraph | Stateful multi-agent orchestration with conditional routing |
| Python | Tool functions, mock data, CLI output |
| Rich | Formatted terminal output |
