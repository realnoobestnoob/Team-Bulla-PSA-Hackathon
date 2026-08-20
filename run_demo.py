#!/usr/bin/env python3
"""
Green Port Control Tower — Demo Runner
Run: python run_demo.py
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

from graph import app
from state import PortState

console = Console()


def print_header():
    console.print(Panel(
        "[bold cyan]🏗  GREEN PORT CONTROL TOWER  🏗[/bold cyan]\n"
        "[dim]PSA Code Sprint 2.0 — Agentic AI Sustainability Demo[/dim]",
        border_style="cyan", expand=False,
    ))


def print_scenario(port_data: dict):
    console.print("\n[bold]📋 SCENARIO[/bold]")

    trucks = port_data["trucks"]
    idle     = sum(1 for t in trucks.values() if t["status"] == "idle")
    charging = sum(1 for t in trucks.values() if t["status"] == "charging")
    epm      = sum(1 for t in trucks.values() if t["type"] == "ePM")

    moves   = port_data["container_moves"]
    high    = sum(1 for m in moves if m["priority"] == "high")
    reefers = sum(1 for m in moves if m["reefer"])

    cranes_down = sum(1 for s in port_data["cranes"].values() if s == "maintenance")
    grid_pct = round(port_data["grid_load_kw"] / port_data["grid_capacity_kw"] * 100)

    tbl = Table(box=box.SIMPLE, show_header=False)
    tbl.add_column(style="dim", width=22)
    tbl.add_column()
    tbl.add_row("Time window",  f"{port_data['time']} → {port_data['deadline']}")
    tbl.add_row("Weather",      f"[red]{port_data['weather'].replace('_', ' ').title()}[/red]")
    tbl.add_row("Grid load",    f"{port_data['grid_load_kw']}/{port_data['grid_capacity_kw']} kW  ({grid_pct}%)")
    tbl.add_row("Trucks",       f"{len(trucks)} total  ({epm} ePM)  |  {idle} idle, {charging} charging")
    tbl.add_row("Cranes down",  f"{cranes_down} of {len(port_data['cranes'])}")
    tbl.add_row("Container moves", f"{len(moves)} total  |  {high} HIGH priority  |  {reefers} reefer")
    console.print(tbl)


def print_agent_header(step: int, name: str, emoji: str):
    console.rule(f"[bold]{emoji}  [{step}/4] {name.upper()} AGENT[/bold]")


def print_action_plan(final_state: PortState):
    console.rule("[bold green]✅  FINAL ACTION PLAN[/bold green]")

    plan = final_state["action_plan"]
    if not plan:
        console.print("[red]No actions in plan.[/red]")
        return

    tbl = Table(box=box.ROUNDED, show_lines=True)
    tbl.add_column("#",       style="dim", width=3)
    tbl.add_column("Action",  style="yellow", width=18)
    tbl.add_column("Details", width=30)
    tbl.add_column("Reason",  width=40)
    tbl.add_column("Auth",    width=10)

    for i, a in enumerate(plan, 1):
        auth  = "[green]auto[/green]" if a.get("tag") == "auto" else "[cyan]approved[/cyan]"
        tbl.add_row(
            str(i),
            a.get("action", "?"),
            str(a.get("details", "")),
            a.get("reason", ""),
            auth,
        )
    console.print(tbl)

    # Summary stats
    climate = final_state.get("climate_recs", {})
    co2 = climate.get("total_co2_saved_kg", 0)
    energy = final_state.get("energy_recs", {})
    headroom = energy.get("headroom_kw", "?")

    console.print(f"\n[bold]📊 Impact Summary[/bold]")
    console.print(f"  CO₂ saved vs diesel baseline : [green]{co2} kg[/green]")
    console.print(f"  Grid headroom remaining      : [green]{headroom} kW[/green]")
    console.print(f"  Actions auto-executed        : [green]{sum(1 for a in plan if a.get('tag') in ('auto', None))}[/green]")

    audit = final_state.get("audit_log", [])
    approved_step = next((s for s in audit if s.get("step") == "human_approval"), {})
    console.print(f"  Actions approved by human    : [cyan]{len(approved_step.get('approved', []))}[/cyan]")
    console.print(f"  Actions rejected by human    : [red]{len(approved_step.get('rejected', []))}[/red]")


def main():
    print_header()

    port_data = json.loads(Path("data/port_state.json").read_text())
    print_scenario(port_data)

    initial: PortState = {
        "port_data":     port_data,
        "transport_recs": [],
        "energy_recs":    {},
        "climate_recs":   {},
        "action_plan":    [],
        "escalated":      [],
        "audit_log":      [],
    }

    # Stream node-by-node so progress is visible
    agent_meta = {
        "transport": (1, "Transport", "🚛"),
        "energy":    (2, "Energy",    "⚡"),
        "climate":   (3, "Climate",   "🌿"),
        "decision":  (4, "Decision",  "🧠"),
    }

    final_state = initial
    for step_output in app.stream(initial):
        for node_name, state in step_output.items():
            if node_name in agent_meta:
                n, label, emoji = agent_meta[node_name]
                print_agent_header(n, label, emoji)
            final_state = state

    print_action_plan(final_state)
    console.print("\n[dim]Full audit log saved to: audit_log (in final state)[/dim]\n")


if __name__ == "__main__":
    main()
