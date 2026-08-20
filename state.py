from typing import TypedDict, List


class PortState(TypedDict):
    port_data: dict
    transport_recs: List[dict]
    energy_recs: List[dict]
    climate_recs: List[dict]
    action_plan: List[dict]
    escalated: List[dict]
    audit_log: List[dict]
