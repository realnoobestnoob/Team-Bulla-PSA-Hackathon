from langgraph.graph import StateGraph, END
from state import PortState
from agents.transport import run_transport_agent
from agents.energy import run_energy_agent
from agents.climate import run_climate_agent
from agents.decision import run_decision_agent
from approval import approval_node


def transport_node(state: PortState) -> PortState:
    recs = run_transport_agent(state["port_data"])
    return {**state, "transport_recs": recs,
            "audit_log": state["audit_log"] + [{"step": "transport", "output": recs}]}


def energy_node(state: PortState) -> PortState:
    recs = run_energy_agent(state["port_data"])
    return {**state, "energy_recs": recs,
            "audit_log": state["audit_log"] + [{"step": "energy", "output": recs}]}


def climate_node(state: PortState) -> PortState:
    recs = run_climate_agent(state["port_data"], state["transport_recs"])
    return {**state, "climate_recs": recs,
            "audit_log": state["audit_log"] + [{"step": "climate", "output": recs}]}


def decision_node(state: PortState) -> PortState:
    plan, escalated = run_decision_agent(
        state["port_data"],
        state["transport_recs"],
        state["energy_recs"],
        state["climate_recs"],
    )
    return {**state, "action_plan": plan, "escalated": escalated,
            "audit_log": state["audit_log"] + [{"step": "decision", "output": plan}]}


def route_after_decision(state: PortState) -> str:
    return "approval" if state["escalated"] else END


builder = StateGraph(PortState)
builder.add_node("transport", transport_node)
builder.add_node("energy",    energy_node)
builder.add_node("climate",   climate_node)
builder.add_node("decision",  decision_node)
builder.add_node("approval",  approval_node)

builder.set_entry_point("transport")
builder.add_edge("transport", "energy")
builder.add_edge("energy",    "climate")
builder.add_edge("climate",   "decision")
builder.add_conditional_edges("decision", route_after_decision,
                               {"approval": "approval", END: END})
builder.add_edge("approval", END)

app = builder.compile()
