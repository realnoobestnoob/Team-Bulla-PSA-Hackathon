from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box

console = Console()


def show_impact(baseline: dict, projected: dict):
    tbl = Table(box=box.SIMPLE, show_header=True)
    tbl.add_column("Metric", style="dim")
    tbl.add_column("Baseline (all diesel)", justify="right")
    tbl.add_column("Proposed plan", justify="right", style="green")

    tbl.add_row("Jobs covered",      str(baseline["jobs_covered"]),  str(projected["jobs_covered"]))
    tbl.add_row("CO₂ emitted (kg)",  str(baseline["co2_kg"]),        str(projected["co2_kg"]))
    tbl.add_row("CO₂ saved (kg)",    "—",                            f"[green]{projected.get('co2_saved_kg',0)}[/green]")
    tbl.add_row("Grid load (kW)",    "—",                            str(projected.get("projected_grid_kw","?")))
    tbl.add_row("Grid safe",         "—",                            "[green]Yes[/green]" if projected.get("grid_safe") else "[red]No[/red]")
    tbl.add_row("Delayed jobs",      "—",                            str(projected.get("delayed_jobs",0)))
    console.print(tbl)


def show_actions(actions: list):
    tbl = Table(box=box.ROUNDED, show_lines=True)
    tbl.add_column("#",      style="dim", width=3)
    tbl.add_column("Type",   style="yellow", width=14)
    tbl.add_column("Params", width=30)
    tbl.add_column("Reason", width=42)
    tbl.add_column("Risk",   width=8)
    tbl.add_column("Valid",  width=6)

    for i, a in enumerate(actions, 1):
        valid_str = "[green]✓[/green]" if a.get("valid", True) else "[red]✗[/red]"
        risk = a.get("risk","low")
        risk_str = f"[red]{risk}[/red]" if risk == "high" else f"[yellow]{risk}[/yellow]" if risk == "medium" else risk
        tbl.add_row(
            str(i), a.get("type","?"),
            str(a.get("parameters",{})),
            a.get("reason","")[:42],
            risk_str, valid_str,
        )
    console.print(tbl)


def human_approval(workflow_state: dict) -> dict:
    validated = workflow_state["validated_actions"]
    baseline  = workflow_state["baseline_metrics"]
    projected = workflow_state["projected_metrics"]

    console.rule("[bold cyan]📋 PROPOSED ACTION PLAN[/bold cyan]")
    show_actions(validated)

    console.rule("[bold cyan]📊 IMPACT ASSESSMENT[/bold cyan]")
    show_impact(baseline, projected)

    invalid = [a for a in validated if not a.get("valid", True)]
    if invalid:
        console.print(f"[red]⚠  {len(invalid)} action(s) failed validation and will be skipped.[/red]")

    console.rule("[bold yellow]👤 SUPERVISOR DECISION[/bold yellow]")
    choice = Prompt.ask(
        "  Decision",
        choices=["approve", "replan", "quit"],
        default="approve"
    )

    if choice == "approve":
        console.print("[green]✓ Plan approved. Executing...[/green]\n")
        return {**workflow_state,
                "pending_approval": [a for a in validated if a.get("valid", True)],
                "human_decision": "approved",
                "audit_log": workflow_state["audit_log"] + [{"step":"human","decision":"approved"}]}

    elif choice == "replan":
        reason = Prompt.ask("  Reason for replanning (e.g. prioritise J04, avoid V02)")
        console.print(f"[yellow]↺ Replanning with constraint: {reason}[/yellow]\n")
        return {**workflow_state,
                "human_decision": "replanning",
                "replan_reason": reason,
                "replan_count": workflow_state.get("replan_count", 0) + 1,
                "audit_log": workflow_state["audit_log"] + [{"step":"human","decision":"replan","reason":reason}]}

    else:
        console.print("[red]Demo ended by supervisor.[/red]")
        raise SystemExit(0)
