from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from state import PortState

console = Console()


def approval_node(state: PortState) -> PortState:
    approved, rejected = [], []

    for action in state["escalated"]:
        details = action.get("details", {})
        reason  = action.get("reason", "N/A")
        console.print(Panel(
            f"[bold]Action:[/bold]  [yellow]{action.get('action', '?').upper()}[/yellow]  {details}\n"
            f"[bold]Reason:[/bold]  {reason}",
            title="[bold red]⚠  HUMAN APPROVAL REQUIRED[/bold red]",
            border_style="red",
        ))
        choice = Prompt.ask("  Approve?", choices=["y", "n"], default="n")
        if choice == "y":
            approved.append({**action, "approved_by": "supervisor"})
            console.print("  [green]✓ Approved[/green]\n")
        else:
            rejected.append({**action, "rejected_by": "supervisor"})
            console.print("  [red]✗ Rejected — action skipped[/red]\n")

    auto_actions = [a for a in state["action_plan"] if a.get("tag") == "auto"]
    final_plan = auto_actions + approved

    return {
        **state,
        "action_plan": final_plan,
        "audit_log": state["audit_log"] + [{
            "step": "human_approval",
            "approved": [a.get("action") for a in approved],
            "rejected": [a.get("action") for a in rejected],
        }],
    }
