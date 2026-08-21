"""
Action Executor + State Manager.
Applies approved, validated actions to port_state.
AI never calls this directly — only reached after human approval.
"""
import copy


def execute_actions(actions: list, port_state: dict) -> tuple:
    """
    Apply approved actions to a copy of port_state.
    Returns (updated_port_state, executed_actions, audit_entries).
    """
    state = copy.deepcopy(port_state)
    executed = []
    audit = []

    for a in actions:
        atype = a.get("type")
        params = a.get("parameters", {})

        if atype == "dispatch":
            vid, jid = params.get("vehicle_id"), params.get("job_id")
            if vid in state["vehicles"] and jid in state["jobs"]:
                state["vehicles"][vid]["status"] = "dispatched"
                state["vehicles"][vid]["assigned_job"] = jid
                state["jobs"][jid]["status"] = "assigned"
                state["jobs"][jid]["assigned_vehicle"] = vid
                executed.append({**a, "status": "executed"})
                audit.append({"action": f"Dispatched {vid} → {jid}", "result": "success"})

        elif atype == "delay_job":
            jid = params.get("job_id")
            delay = params.get("delay_mins", 30)
            if jid in state["jobs"]:
                state["jobs"][jid]["status"] = "delayed"
                state["jobs"][jid]["delay_mins"] = delay
                executed.append({**a, "status": "executed"})
                audit.append({"action": f"Delayed {jid} by {delay} mins", "result": "success"})

        elif atype == "recharge":
            vid = params.get("vehicle_id")
            if vid in state["vehicles"]:
                state["vehicles"][vid]["status"] = "charging"
                executed.append({**a, "status": "executed"})
                audit.append({"action": f"Sent {vid} to charge", "result": "success"})

    return state, executed, audit
