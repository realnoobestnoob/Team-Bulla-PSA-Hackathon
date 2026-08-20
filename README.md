# Green Port Control Tower
**PSA Code Sprint 2.0** — Agentic AI for Port Sustainability

## Problem
PSA port operations involve interconnected trade-offs: charging more ePMs reduces emissions but strains the grid. Dispatching more trucks clears cargo faster but increases congestion. Rain raises safety risk for reefer containers. No single decision can be made in isolation.

## Solution
A multi-agent AI control tower that receives an operational scenario and coordinates across transport, energy, and climate objectives — with human approval for high-risk actions.

## Architecture
```
Scenario (JSON)
      │
      ▼
 Transport Agent  →  assigns ePM trucks to high-priority moves
      │
 Energy Agent     →  checks grid load, reschedules charging if needed
      │
 Climate Agent    →  calculates CO₂ saved, flags weather/reefer risk
      │
 Decision Engine  →  unified action plan (auto vs escalate)
      │
 Human Approval   →  supervisor approves/rejects escalated actions
      │
 Action Log + Summary
```

## Stack
- **Claude API** (claude-sonnet-4-6) — reasoning and decision-making
- **LangGraph** — stateful multi-agent orchestration
- **Python** — tools, mock data, CLI

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env        # add your ANTHROPIC_API_KEY
python run_demo.py
```

## Demo Scenario
10 ePM trucks, 10 container moves, 2 cranes down, heavy rain, grid at 80% capacity.

Expected output: 4 truck dispatches (auto) + 1 charging delay (auto) + 2 escalations (reefer safety in rain → human decision).

## Evaluation Criteria Mapping
| Criterion | How it's addressed |
|-----------|-------------------|
| Reasoning | Each agent reasons over constraints before acting |
| Tool orchestration | 6 distinct tools across 3 agents |
| State management | LangGraph PortState tracks truck/grid/move status |
| Human oversight | Escalation node with approve/reject |
| Scalability | Add agents/tools without changing orchestration |
| Responsible AI | Audit log, safety guardrails, no auto-approval of high-risk actions |
