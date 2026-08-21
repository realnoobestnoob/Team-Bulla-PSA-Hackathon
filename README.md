# Updates!
- Generated barely working skeletal model

# To-do!!!
- Improve overall model complexity
- Improve UI of output in terminal/deploy on streamlit
- Optimize token usage
- Generate means to evaluate model performance (KPI/metrics/some sort of score). Can use jupyter notebook to make some charts for the presentation

# Notes
- Using gemini 3.6 flash via google ai studio
- Use AI agents for decision making; the rest use conventional code

# 🏗️ Green Port Control Tower
**PSA Code Sprint 2.0** — Agentic AI for Port Sustainability

## How it works

```
Load Scenario (JSON files)
        ↓
   Build PortState
        ↓
Control Tower AI  →  calls tools  →  proposes actions
        ↓
  Constraint Validator  (deterministic)
        ↓
  Impact Evaluator  (CO₂ / energy / delays)
        ↓
  Human Supervisor  →  approve / replan
        ↓              ↑ (loops back if replanning)
  Action Executor
        ↓
  Updated Port State + Audit Log
```

> **AI proposes. Code validates. Humans decide. Code executes. State records.**

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Add your API key**
```bash
cp .env.example .env
# edit .env and set GOOGLE_API_KEY=your_key_here
```

**3. Run the demo**
```bash
python run_demo.py              # heavy rain scenario (default)
python run_demo.py normal       # normal operations
```

## Project structure

```
green_port_agent/
├── run_demo.py              # entry point
├── loader.py                # loads JSON files → runtime PortState
├── state.py                 # WorkflowState schema
├── validator.py             # deterministic constraint checker
├── impact.py                # CO₂ / energy / delay metrics
├── executor.py              # applies approved actions to state
├── approval.py              # human supervisor CLI
├── graph.py                 # LangGraph orchestration
│
├── agents/
│   ├── base.py              # Google AI tool-calling loop
│   └── control_tower.py     # single Control Tower AI agent
│
├── tools/
│   ├── route.py             # get_vehicle_options, calculate_route
│   ├── emissions.py         # estimate_emissions
│   ├── energy.py            # check_energy_impact
│   └── weather.py           # check_weather_risk
│
├── data/
│   ├── vehicles.json
│   ├── jobs.json
│   ├── weather.json
│   ├── equipment.json
│   ├── charging_stations.json
│   ├── energy.json
│   ├── objectives.json
│   └── scenarios/
│       ├── heavy_rain.json
│       └── normal.json
│
├── requirements.txt
├── .env.example
└── .gitignore
```

## Demo flow (~8 minutes)

1. **Port state loaded** — 10 vehicles, 10 jobs, heavy rain, grid at 80%
2. **Control Tower AI** calls tools to evaluate each high-priority job, checks emissions and weather risk, proposes an action plan
3. **Validator** eliminates any infeasible actions (low battery, already dispatched, etc.)
4. **Impact Evaluator** shows CO₂ saved vs all-diesel baseline
5. **Supervisor** approves — or types a constraint and triggers replan (up to 2 replans)
6. **Executor** applies approved actions, state updates, final summary printed

## Changing the scenario

<<<<<<< HEAD
Edit any file in `data/` to change the environment. Scenario overrides in `data/scenarios/heavy_rain.json` are applied on top of the base data at load time — the source files are never modified.
=======
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
>>>>>>> 57a360f19d095da19fa834088ca6b411634c7132
