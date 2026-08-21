from langgraph.graph import StateGraph, END
from state import WorkflowState
from agents.control_tower import run_control_tower
from validator import validate_all
from impact import compute_baseline, compute_projected
from executor import execute_actions
from approval import human_approval
from rich.console import Console
from rich.rule import Rule

console = Console()
MAX_REPLANS = 2


# ── Nodes ────────────────────────────────────────────────────────────────────

def planner_node(state: WorkflowState) -> WorkflowState:
    console.rule("[bold green]🧠 CONTROL TOWER AI — Planning[/bold green]")
    replan = state.get("replan_reason", "")
    if replan:
        console.print(f"  [yellow]Replanning #{state.get('replan_count',1)}: {replan}[/yellow]")
    actions = run_control_tower(state["port_state"], replan_reason=replan)
    console.print(f"  [green]✓ {len(actions)} action(s) proposed[/green]")
    return {**state,
            "proposed_actions": actions,
            "audit_log": state["audit_log"] + [{"step":"planner","actions_proposed":len(actions)}]}


def validator_node(state: WorkflowState) -> WorkflowState:
    console.rule("[bold blue]✅ CONSTRAINT VALIDATOR[/bold blue]")
    validated = validate_all(state["proposed_actions"], state["port_state"])
    valid_n   = sum(1 for a in validated if a.get("valid"))
    invalid_n = len(validated) - valid_n
    console.print(f"  [green]{valid_n} valid[/green]  [red]{invalid_n} invalid[/red]")
    return {**state,
            "validated_actions": validated,
            "audit_log": state["audit_log"] + [{"step":"validator","valid":valid_n,"invalid":invalid_n}]}


def impact_node(state: WorkflowState) -> WorkflowState:
    console.rule("[bold magenta]📊 IMPACT EVALUATOR[/bold magenta]")
    baseline  = compute_baseline(state["port_state"])
    projected = compute_projected(state["validated_actions"], state["port_state"])
    console.print(f"  CO₂ saved: [green]{projected.get('co2_saved_kg',0)} kg[/green]  "
                  f"Grid: [{'green' if projected.get('grid_safe') else 'red'}]{projected.get('projected_grid_kw','?')} kW[/]")
    return {**state, "baseline_metrics": baseline, "projected_metrics": projected,
            "audit_log": state["audit_log"] + [{"step":"impact","co2_saved":projected.get("co2_saved_kg")}]}


def approval_node(state: WorkflowState) -> WorkflowState:
    console.rule("[bold yellow]👤 HUMAN SUPERVISOR[/bold yellow]")
    return human_approval(state)


def executor_node(state: WorkflowState) -> WorkflowState:
    console.rule("[bold cyan]⚙  ACTION EXECUTOR[/bold cyan]")
    new_port_state, executed, audit_entries = execute_actions(
        state["pending_approval"], state["port_state"]
    )
    for e in audit_entries:
        console.print(f"  [green]✓ {e['action']}[/green]")
    return {**state,
            "port_state": new_port_state,
            "executed_actions": state["executed_actions"] + executed,
            "audit_log": state["audit_log"] + [{"step":"executor","entries":audit_entries}]}


# ── Routing ──────────────────────────────────────────────────────────────────

def route_after_approval(state: WorkflowState) -> str:
    if state.get("human_decision") == "replanning" and state.get("replan_count",0) <= MAX_REPLANS:
        return "planner"
    return "executor"


# ── Graph ────────────────────────────────────────────────────────────────────

builder = StateGraph(WorkflowState)
builder.add_node("planner",   planner_node)
builder.add_node("validator", validator_node)
builder.add_node("impact",    impact_node)
builder.add_node("approval",  approval_node)
builder.add_node("executor",  executor_node)

builder.set_entry_point("planner")
builder.add_edge("planner",   "validator")
builder.add_edge("validator", "impact")
builder.add_edge("impact",    "approval")
builder.add_conditional_edges("approval", route_after_approval,
                               {"planner": "planner", "executor": "executor"})
builder.add_edge("executor", END)

app = builder.compile()
