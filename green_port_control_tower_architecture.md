# Green Port Control Tower — Architecture & Feature Specification

## 1. Purpose

The Green Port Control Tower is a prototype decision-support system for port operations that combines operational data, sustainability metrics, deterministic tools, AI-assisted planning, and human oversight.

The system is designed around one central principle:

> **AI should recommend and reason; deterministic software should validate and execute; humans should retain control over consequential decisions.**

The prototype should demonstrate how a port can respond to changing operational conditions while balancing:

- Operational efficiency
- Carbon emissions
- Energy demand
- Resilience and disruption risk
- Operational constraints
- Human priorities and judgement

The architecture is intentionally designed to be achievable within a short hackathon timeframe while still demonstrating a credible path toward a more production-grade control-tower system.

---

# 2. Design Goals

The architecture should satisfy six goals.

### 2.1 Maintain a reliable representation of the port

The system needs a single authoritative representation of what is happening in the simulated port at any point in time.

### 2.2 Separate reasoning from execution

The AI should not directly modify the operational environment. It should propose actions, while deterministic code checks and executes them.

### 2.3 Keep humans in the decision loop

Human involvement should be meaningful rather than simply being an approval button. Humans should be able to reject actions, change priorities, or impose constraints and trigger replanning.

### 2.4 Make sustainability measurable

The system should compare the proposed plan against a baseline and show measurable changes in emissions, energy consumption, waiting time, delays, or other relevant metrics.

### 2.5 Make decisions explainable

Every recommendation should have a reason, expected impact, risk level, and record of whether it was accepted, modified, or rejected.

### 2.6 Keep the prototype simple enough to implement

The system should avoid unnecessary infrastructure and excessive AI complexity. JSON files, Python state objects, deterministic tools, and one primary AI agent are sufficient for the prototype.

---

# 3. High-Level Architecture

```text
                         ┌──────────────────────┐
                         │      Dashboard       │
                         │    / Demo Interface  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Control Tower     │
                         │     AI / Planner     │
                         └──────────┬───────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
          ┌────────────┐     ┌────────────┐     ┌────────────┐
          │ Route /    │     │ Energy     │     │ Climate /  │
          │ Transport  │     │ Tools      │     │ Environment│
          └────────────┘     └────────────┘     └────────────┘
                 │                  │                  │
                 └──────────────────┼──────────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Candidate / Plan     │
                         │ Generation           │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Constraint & Action  │
                         │ Validator            │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Impact Evaluation    │
                         │ CO₂ / Energy / Time  │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Human Supervisor     │
                         └───────┬────────┬─────┘
                                 │        │
                              Approve    Modify/
                                 │       Reject
                                 │        │
                                 │        ▼
                                 │    Replanning
                                 │
                                 ▼
                         ┌──────────────────────┐
                         │   Action Executor    │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │    State Manager     │
                         │    / PortState       │
                         └──────────┬───────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Updated Port State   │
                         └──────────────────────┘
                                    │
                                    └──────► Re-evaluate
```

The architecture is intentionally stateful. A decision should change the simulated port state, and subsequent decisions should operate on the new state rather than repeatedly analysing the original scenario.

---

# 4. Data Architecture

## 4.1 Separate source files

The initial port data should be separated into logical JSON files.

Recommended structure:

```text
data/
├── vehicles.json
├── jobs.json
├── equipment.json
├── charging_stations.json
├── environment.json
├── objectives.json
└── scenarios/
    ├── normal.json
    ├── heavy_rain.json
    ├── truck_breakdown.json
    └── compound_event.json
```

### Why separate files?

Separate files make the data easier to:

- Locate
- Understand
- Edit
- Version-control
- Replace during testing
- Use for different scenarios

For example, someone changing vehicle information should not need to search through a large `port_state.json`.

Separate scenario data also makes it easy to demonstrate different operational conditions.

---

# 5. Why not keep everything in one JSON object?

A single JSON file is simpler initially:

```json
{
  "vehicles": {...},
  "jobs": {...},
  "weather": {...},
  "energy": {...}
}
```

### Advantages

- Very simple loader
- Easy to understand for a small prototype
- Easy to pass into an initial demo
- Fewer files

### Disadvantages

As the project grows, it becomes difficult to distinguish:

- Static source data
- Current operational state
- Scenario configuration
- Objectives
- Runtime decisions
- Audit history

A large JSON file also encourages the application to treat the file itself as the current state.

### Recommendation

Use separate JSON files as the **input/persistence layer**, but combine them into a single runtime `PortState` through a loader.

This gives us both simplicity and structure.

---

# 6. Runtime PortState

The application should construct a single runtime representation:

```python
PortState
│
├── time
├── vehicles
├── jobs
├── equipment
├── charging_stations
├── weather
├── energy
├── objectives
├── constraints
├── proposed_actions
├── pending_approval
├── executed_actions
├── metrics
└── audit_log
```

The important distinction is:

> **The JSON files describe the starting environment. `PortState` describes the current environment.**

For example:

```python
state["vehicles"]["T03"]
```

represents the current status of T03.

If T03 is dispatched, the runtime state changes.

The original source file does not need to be rewritten.

---

# 7. State Manager

## 7.1 Purpose

The State Manager is one of the most important components.

Its responsibility is to provide a controlled way of reading and modifying the current port state.

Instead of allowing every AI component to directly manipulate data:

```python
state["vehicles"]["T03"]["status"] = "dispatched"
```

the system should use:

```python
state_manager.apply_action(action)
```

The State Manager validates the transition and updates the state consistently.

---

## 7.2 Why a State Manager is necessary

Without a central state manager, different components can develop conflicting views.

For example:

```text
vehicles.json
T03 = available

AI context
T03 = assigned

Dashboard
T03 = available
```

This creates inconsistent behaviour.

The State Manager provides one authoritative source of truth.

---

## 7.3 State transition example

Initial state:

```text
T03 = available
M01 = unassigned
```

AI proposes:

```text
Assign T03 → M01
```

Validator checks:

```text
Does T03 exist?
Is T03 available?
Does M01 exist?
Is M01 unassigned?
Is T03 capable of the job?
Is the battery sufficient?
```

If valid:

```text
T03 = assigned
M01 = assigned
```

The new state becomes the input for subsequent decisions.

---

# 8. Action Model

Actions should be represented explicitly rather than as arbitrary strings.

Example:

```json
{
  "id": "A001",
  "type": "dispatch",
  "parameters": {
    "vehicle_id": "T03",
    "job_id": "M01"
  },
  "reason": "T03 provides the lowest feasible emissions while meeting the job deadline.",
  "risk": "low",
  "estimated_impact": {
    "co2_kg": -2.4,
    "delay_mins": 0,
    "energy_kwh": 8
  },
  "requires_approval": false,
  "status": "proposed"
}
```

An action can move through:

```text
proposed
    ↓
validated
    ↓
pending_approval
    ↓
approved
    ↓
executed
```

or:

```text
proposed → rejected
```

This gives the system a clear lifecycle.

---

# 9. Control Tower AI

## 9.1 Recommended approach

Rather than having multiple independent AI agents, use one primary Control Tower AI with access to specialised deterministic tools.

```text
Control Tower AI
│
├── route tool
├── energy tool
├── emissions tool
├── weather tool
├── simulation tool
└── state query tools
```

The AI's responsibility is to:

1. Understand the current situation
2. Identify relevant constraints
3. Request calculations from tools
4. Generate candidate actions
5. Explain trade-offs
6. Recommend a plan

It should not be responsible for performing deterministic calculations that can be done reliably in code.

---

# 10. Why one AI agent instead of multiple AI agents?

The previous architecture separated Transport, Energy, Climate, and Decision reasoning into multiple AI agents.

That approach can be useful for a larger system, but it introduces unnecessary complexity for a two-week prototype.

### Multi-agent approach

```text
Transport AI
     ↓
Energy AI
     ↓
Climate AI
     ↓
Decision AI
```

Problems:

- More API calls
- More latency
- Higher cost
- More opportunities for contradictory outputs
- Harder debugging
- More complex state management

### Single Control Tower approach

```text
              Control Tower AI
               /      |      \
          Transport Energy Climate
             tools    tools   tools
```

The AI still has access to domain-specific capabilities, but there is one reasoning layer.

### Recommendation

Use one AI agent plus deterministic domain tools.

The multi-agent architecture can remain a future scalability option.

---

# 11. Deterministic Tools

Tools should be responsible for facts and calculations.

Examples:

```text
calculate_route()
estimate_energy()
calculate_emissions()
check_weather_risk()
find_feasible_vehicles()
simulate_action()
calculate_metrics()
```

The AI asks:

> "Which vehicles can feasibly perform M01?"

The tool determines that.

The AI should not invent the answer.

---

# 12. Constraint Validator

The Constraint Validator is a critical safety layer.

AI-generated actions should never be executed directly.

The flow is:

```text
AI recommendation
       ↓
Action Validator
       ↓
 ┌─────┴─────┐
Valid       Invalid
 ↓             ↓
Execute     Reject/Replan
```

Example constraints:

### Vehicle

- Vehicle exists
- Vehicle is available
- Vehicle has sufficient battery/fuel
- Vehicle is capable of the job
- Vehicle is not already assigned

### Job

- Job exists
- Job is not already completed
- Deadline requirements are satisfied

### Operations

- Equipment availability
- Weather restrictions
- Restricted areas
- Operational safety requirements

---

# 13. Hard Constraints vs Soft Objectives

This distinction is fundamental.

## Hard constraints

These must never be violated.

Examples:

```text
Safety
Equipment capability
Minimum battery
Restricted operating conditions
Critical deadlines
```

These should be enforced deterministically.

## Soft objectives

These can be traded against one another.

Examples:

```text
CO₂ reduction
Energy efficiency
Travel distance
Waiting time
Operational cost
Resilience
```

These can be incorporated into scoring and optimisation.

---

# 14. Objective Weights

The system should not permanently bury priorities inside an AI prompt.

Instead:

```json
{
  "objectives": {
    "operational_efficiency": 0.40,
    "carbon_reduction": 0.30,
    "energy_efficiency": 0.15,
    "resilience": 0.15
  }
}
```

This allows a human to change the priorities.

For example:

```text
Operational efficiency    40%
Carbon reduction          30%
Energy efficiency         15%
Resilience                15%
```

could become:

```text
Operational efficiency    30%
Carbon reduction          40%
Energy efficiency         15%
Resilience                15%
```

The same port state can therefore produce a different recommendation.

---

# 15. Why human control should modify priorities

A simple approval button:

```text
[Approve] [Reject]
```

makes the human a gatekeeper.

A stronger design allows:

```text
AI recommendation
        ↓
Human reviews
        ↓
Human changes priorities
        ↓
AI replans
        ↓
Human approves
```

This better represents human-AI collaboration.

The human contributes:

- Business judgement
- Operational priorities
- Risk tolerance
- Exceptions
- Context unavailable to the model

The AI contributes:

- Rapid analysis
- Scenario comparison
- Calculation orchestration
- Recommendation generation

---

# 16. Action Execution

Once an action is approved, it should actually affect the simulation.

Example:

```text
Approved:
Dispatch T03 → M01
```

Executor:

```text
T03.status = "dispatched"
T03.current_location = M01.destination
T03.battery_pct -= estimated_consumption

M01.status = "in_progress"
```

The resulting state is then used by the next planning cycle.

This is what turns the system from a recommendation engine into a basic control-tower simulation.

---

# 17. Replanning

The system should support replanning after:

- A human rejection
- A human priority change
- A new weather event
- Vehicle breakdown
- Battery depletion
- Equipment failure
- Energy constraints changing

Example:

```text
Initial state
     ↓
AI recommendation
     ↓
Human rejects
     ↓
Reason/constraint updated
     ↓
AI replans
     ↓
New recommendation
```

This is preferable to simply removing rejected actions.

---

# 18. Human-in-the-Loop Example

Consider:

```text
Heavy rain approaching Zone B
3 vehicles charging
2 cranes unavailable
10 pending jobs
```

The AI evaluates the situation.

It recommends:

```text
Use EV T03 for M01
Delay M03
Keep T10 charging
```

The human sees:

```text
Reason:
T03 minimises estimated emissions while
meeting the M01 deadline.
```

The human then changes:

```text
Customer priority for M03:
NORMAL → CRITICAL
```

The system replans.

It may now recommend:

```text
Use diesel T08 for M03
Use EV T03 for M01
Delay M07
```

The important point is that the human did not merely approve or reject an AI answer.

They changed the operational context.

---

# 19. Sustainability Evaluation

The system should compare the AI plan against a baseline.

Example:

```text
                  Baseline      Optimised

CO₂                1,500 kg       1,200 kg
Empty distance       340 km         210 km
Waiting time          87 min          51 min
Late jobs              6              2
Peak grid load       2,400 kW       2,200 kW
```

Then display:

```text
CO₂ reduction: 20%
Empty distance: 38% reduction
Waiting time: 41% reduction
Late jobs: 67% reduction
```

The numbers should be described as **simulation results** unless they are based on validated PSA operational data.

---

# 20. Emissions Model

The prototype should clearly define what "CO₂" means.

A simple initial model can use:

```text
Diesel emissions
= distance × fuel/emission factor
```

For electric vehicles, there are two possible approaches.

### Alternative A — Tailpipe emissions

```text
EV = 0 tailpipe CO₂
```

Advantages:

- Simple
- Easy to explain
- Easy to implement

Disadvantage:

- Does not represent electricity-generation emissions

### Alternative B — Electricity-based emissions

```text
EV CO₂
= electricity consumed × grid emission factor
```

Advantages:

- Better connects energy and sustainability
- Allows charging-time optimisation

Disadvantage:

- Requires more assumptions/data

### Recommendation

For the two-week prototype, use the simpler approach if necessary, but explicitly label it as **tailpipe CO₂**. If time allows, add a configurable grid emission factor.

---

# 21. Energy Model

Energy calculations should be based on actual state changes.

Avoid simply subtracting a fixed amount because a dispatch action exists.

Instead:

```text
Current state
    ↓
Candidate action
    ↓
Simulate action
    ↓
Calculate:
    vehicle energy use
    charging changes
    grid demand
    resulting battery levels
```

This makes energy impact consistent with the rest of the simulation.

---

# 22. Weather / Resilience Model

The environmental component should combine:

```text
Weather risk
+
Operational emissions
+
Resilience impact
```

For example:

```text
Heavy rain
    ↓
Route risk increases
    ↓
Travel time increases
    ↓
Certain routes become unsuitable
    ↓
Alternative vehicle/job assignment
```

The weather system should influence the operational state rather than merely produce a textual warning.

---

# 23. Scenario System

A scenario system is strongly recommended for the prototype.

Example:

```text
scenarios/
├── normal.json
├── heavy_rain.json
├── vehicle_breakdown.json
├── energy_peak.json
└── compound_disruption.json
```

The demo can then allow:

```text
Scenario:
[ Compound disruption ▼ ]

[ Run ]
```

A strong demonstration scenario might contain:

```text
Heavy rain
+
EV battery shortage
+
Vehicle breakdown
+
Two cranes unavailable
+
High energy demand
```

The Control Tower must then find a workable plan.

---

# 24. Why scenarios are preferable to hard-coding a single demo

A single hard-coded scenario can demonstrate the happy path, but it does not prove that the system responds dynamically.

Scenarios allow the team to demonstrate:

```text
Same architecture
      +
Different conditions
      ↓
Different recommendations
```

This is much more convincing.

---

# 25. Audit Log

Every significant decision should be recorded.

Example:

```json
{
  "timestamp": "14:03",
  "actor": "control_tower_agent",
  "action": "dispatch",
  "input_state_version": 17,
  "reason": "Lowest feasible emissions while meeting deadline.",
  "estimated_impact": {
    "co2_kg": -2.4,
    "delay_mins": 0
  },
  "human_decision": "approved",
  "actual_outcome": {
    "co2_kg": 4.8
  }
}
```

This provides:

- Explainability
- Debugging
- Reproducibility
- Accountability
- A basis for evaluating AI performance

---

# 26. State Versioning

A simple integer state version can make the prototype much easier to debug.

Example:

```text
State v1
   ↓
Dispatch T03
   ↓
State v2
   ↓
Charge T05
   ↓
State v3
```

Actions can then record:

```text
action A014
created against state v2
```

This is a lightweight way of preventing confusion about which version of the port the AI was reasoning about.

---

# 27. Proposed Project Structure

A practical implementation could look like:

```text
Team-Bulla-PSA-Hackathon/
│
├── app/
│   ├── main.py
│   │
│   ├── agents/
│   │   └── control_tower.py
│   │
│   ├── state/
│   │   ├── models.py
│   │   ├── loader.py
│   │   └── state_manager.py
│   │
│   ├── tools/
│   │   ├── transport.py
│   │   ├── energy.py
│   │   ├── emissions.py
│   │   ├── weather.py
│   │   └── simulation.py
│   │
│   ├── decision/
│   │   ├── validator.py
│   │   └── evaluator.py
│   │
│   └── ui/
│       └── dashboard.py
│
├── data/
│   ├── vehicles.json
│   ├── jobs.json
│   ├── equipment.json
│   ├── charging_stations.json
│   ├── environment.json
│   ├── objectives.json
│   └── scenarios/
│
├── tests/
│
└── README.md
```

This is a recommended architecture rather than a requirement to reproduce every directory immediately.

---

# 28. End-to-End Workflow

The complete workflow is:

```text
1. Load scenario
        ↓
2. Build PortState
        ↓
3. Control Tower reads current state
        ↓
4. AI identifies decisions that need to be made
        ↓
5. Tools provide deterministic information
        ↓
6. Candidate actions are generated
        ↓
7. Hard constraints eliminate invalid actions
        ↓
8. Candidate plans are evaluated
        ↓
9. AI explains the preferred plan
        ↓
10. Human reviews
        ↓
   ┌──────┴────────┐
   ↓               ↓
Approve          Modify/Reject
   ↓               ↓
   │             Replan
   │               ↓
   └───────┬───────┘
           ↓
11. Action Executor
           ↓
12. State Manager updates PortState
           ↓
13. Metrics recalculated
           ↓
14. Audit log updated
           ↓
15. Dashboard shows new state
```

This creates a closed loop.

---

# 29. What the AI should and should not do

## AI should

- Interpret the situation
- Identify trade-offs
- Decide which tools to call
- Generate candidate plans
- Explain recommendations
- Adapt to human priorities
- Replan after changes

## AI should not

- Invent operational data
- Directly modify the state
- Bypass safety constraints
- Perform calculations that deterministic tools can perform
- Decide whether an unsafe action is allowed
- Be the source of truth for current port state

This separation is central to making the architecture reliable.

---

# 30. Alternatives Considered

## Alternative 1 — One giant JSON object

### Pros

- Very simple
- Minimal code
- Good for a tiny prototype

### Cons

- Poor separation of data
- Harder scenario management
- Encourages treating static data as runtime state
- Becomes unwieldy as features grow

### Recommendation

Use separate source JSON files and combine them into `PortState` at runtime.

---

## Alternative 2 — Database

A SQLite/PostgreSQL database could replace JSON.

### Pros

- Better persistence
- Queries
- Concurrent access
- More realistic production architecture

### Cons

- More setup
- More code
- Unnecessary for a two-week prototype
- More infrastructure to debug

### Recommendation

Use JSON now. A database is a natural future upgrade.

---

## Alternative 3 — Multiple AI agents

### Pros

- Clear domain separation
- Potentially scalable
- Each agent can specialise

### Cons

- More complexity
- More API calls
- Harder coordination
- Conflicting recommendations
- More difficult state management

### Recommendation

Use one Control Tower AI with specialised tools for the prototype.

---

## Alternative 4 — Pure deterministic optimisation

The system could use only optimisation algorithms without an LLM.

### Pros

- Highly deterministic
- Reproducible
- Easy to validate

### Cons

- Less flexible natural-language interaction
- Harder to incorporate ambiguous human instructions
- Less compelling demonstration of AI capabilities

### Recommendation

Use deterministic optimisation/validation underneath an AI reasoning layer.

The AI handles reasoning and orchestration; deterministic software handles constraints and calculations.

---

## Alternative 5 — AI directly executes tools

### Pros

- Very simple agent architecture

### Cons

- Dangerous
- Difficult to validate
- Allows invalid actions
- Makes debugging harder

### Recommendation

AI → proposal → validation → human decision → execution.

---

# 31. Two-Week MVP

The architecture should be implemented incrementally.

## Phase 1 — Core state

Implement:

```text
JSON files
    ↓
Loader
    ↓
PortState
    ↓
State Manager
```

---

## Phase 2 — Deterministic tools

Implement:

```text
Route
Energy
Emissions
Weather
Constraint validation
```

Do not focus on AI yet.

---

## Phase 3 — Control Tower

Add one AI agent capable of:

```text
Read state
→ call tools
→ propose actions
→ explain reasoning
```

---

## Phase 4 — Human loop

Add:

```text
Approve
Reject
Modify priority
Replan
```

---

## Phase 5 — Execution

Implement:

```text
Approved action
    ↓
Action Executor
    ↓
State update
    ↓
New metrics
```

---

## Phase 6 — Demo

Add:

- Scenario selector
- Current port state
- AI recommendation
- Reasoning/explanation
- Expected sustainability impact
- Human controls
- Updated state
- Baseline comparison
- Audit log

---

# 32. Recommended Demo Story

The strongest demonstration is not:

> "Look, an AI generated a recommendation."

Instead:

> **"Watch the control tower respond to a changing port."**

Example:

```text
Initial scenario
↓
Heavy rain + equipment shortage + high energy demand
↓
AI analyses operational and sustainability trade-offs
↓
AI recommends a plan
↓
Human changes priority:
customer deadline becomes critical
↓
AI replans
↓
Human approves
↓
Actions execute
↓
Port state changes
↓
Energy / emissions / delays are recalculated
↓
Dashboard shows the result
```

This demonstrates the architecture rather than merely the AI.

---

# 33. Core Architectural Principle

The entire system can be summarised as:

```text
                 HUMAN
                   │
             priorities /
              judgement
                   │
                   ▼
             ┌───────────┐
             │    AI     │
             │ reasoning │
             └─────┬─────┘
                   │
             recommendations
                   │
                   ▼
             ┌───────────┐
             │ Validator │
             └─────┬─────┘
                   │
              valid actions
                   │
                   ▼
             ┌───────────┐
             │ Executor  │
             └─────┬─────┘
                   │
                   ▼
             ┌───────────┐
             │   State   │
             │  Manager  │
             └─────┬─────┘
                   │
                   ▼
             CURRENT PORT
                STATE
```

The fundamental separation is:

> **AI proposes. Code validates. Humans decide. Code executes. State records the result.**

That principle should guide the implementation of every feature in the Green Port Control Tower.
