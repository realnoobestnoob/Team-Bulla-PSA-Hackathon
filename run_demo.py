#!/usr/bin/env python3
"""
Green Port Control Tower — Demo Runner
Usage: python run_demo.py [scenario]
Scenarios: heavy_rain (default) | normal
"""
import sys, os, json
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    print("ERROR: GOOGLE_API_KEY not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

from loader import load_port_state
from graph import app
from state import WorkflowState

console = Console()
SCENARIO = sys.argv[1] if len(sys.argv) > 1 else "heavy_rain"


def print_header(scenario: str):
    console.print(Panel(
        "[bold cyan]🏗  GREEN PORT CONTROL TOWER[/bold cyan]\n"
        f"[dim]PSA Code Sprint 2.0  |  Scenario: {scenario.replace('_',' ').title()}[/dim]",
        border_style="cyan", expand=False,
    ))


def print_port_state(port_state: dict):
    console.print("\n[bold]📋 PORT STATE[/bold]")

    vehicles = port_state["vehicles"]
    jobs     = port_state["jobs"]
    weather  = port_state["weather"]
    energy   = port_state["energy"]

    idle     = sum(1 for v in vehicles.values() if v.get("status") == "idle")
    electric = sum(1 for v in vehicles.values() if v.get("type") == "electric")
    high_j   = sum(1 for j in jobs.values() if j.get("priority") == "high")
    grid_pct = round(energy["grid_load_kw"] / energy["grid_capacity_kw"] * 100)

    tbl = Table(box=box.SIMPLE, show_header=False)
    tbl.add_column(style="dim", width=22)
    tbl.add_column()
    tbl.add_row("Vehicles",    f"{len(vehicles)} total  ({electric} electric, {len(vehicles)-electric} diesel)  |  {idle} idle")
    tbl.add_row("Jobs",        f"{len(jobs)} total  |  {high_j} HIGH priority")
    tbl.add_row("Weather",     f"[red]{weather.get('condition','?').replace('_',' ').title()}[/red]  |  Wind: {weather.get('wind_speed','?')} km/h")
    tbl.add_row("Grid load",   f"{energy['grid_load_kw']}/{energy['grid_capacity_kw']} kW  ({grid_pct}%)")
    console.print(tbl)


def print_final_summary(final_state: dict):
    console.rule("[bold green]✅ FINAL SUMMARY[/bold green]")

    executed = final_state.get("executed_actions", [])
    projected = final_state.get("projected_metrics", {})
    baseline  = final_state.get("baseline_metrics", {})

    tbl = Table(box=box.ROUNDED)
    tbl.add_column("Metric")
    tbl.add_column("Baseline", justify="right")
    tbl.add_column("Achieved", justify="right", style="green")

    tbl.add_row("Jobs covered",    str(baseline.get("jobs_covered","?")), str(len(executed)))
    tbl.add_row("CO₂ emitted kg",  str(baseline.get("co2_kg","?")),      str(projected.get("co2_kg","?")))
    tbl.add_row("CO₂ saved kg",    "—",                                   f"[green]{projected.get('co2_saved_kg','?')}[/green]")
    tbl.add_row("Grid headroom kW","—",                                   str(projected.get("headroom_kw","?")))
    console.print(tbl)

    console.print(f"\n[bold]Audit log:[/bold] {len(final_state.get('audit_log',[]))} entries recorded")


def main():
    print_header(SCENARIO)
    port_state = load_port_state(SCENARIO)
    print_port_state(port_state)

    initial: WorkflowState = {
        "port_state":        port_state,
        "proposed_actions":  [],
        "validated_actions": [],
        "pending_approval":  [],
        "executed_actions":  [],
        "rejected_actions":  [],
        "baseline_metrics":  {},
        "projected_metrics": {},
        "replan_count":      0,
        "replan_reason":     "",
        "human_decision":    "",
        "audit_log":         [],
    }

    final_state = initial
    for chunk in app.stream(initial):
        for _, state in chunk.items():
            final_state = state

    print_final_summary(final_state)


if __name__ == "__main__":
    main()
