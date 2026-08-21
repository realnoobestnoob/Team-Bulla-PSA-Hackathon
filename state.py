from typing import TypedDict, List


class WorkflowState(TypedDict):
    # Port data (runtime)
    port_state: dict          # vehicles, jobs, equipment, weather, energy, objectives, charging_stations

    # Workflow
    proposed_actions: List[dict]
    validated_actions: List[dict]
    pending_approval: List[dict]
    executed_actions: List[dict]
    rejected_actions: List[dict]

    # Metrics
    baseline_metrics: dict    # before any actions
    projected_metrics: dict   # after proposed actions

    # Replanning
    replan_count: int
    replan_reason: str
    human_decision: str       # "approved" | "replanning"

    # Audit
    audit_log: List[dict]
