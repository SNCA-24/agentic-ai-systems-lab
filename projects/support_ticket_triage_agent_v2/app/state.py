from typing import Any, Literal, Optional
from typing_extensions import TypedDict


Category = Literal["billing", "refund", "technical", "general", "unknown"]
RiskLevel = Literal["low", "medium", "high"]
ApprovalStatus = Literal["not_required", "pending", "approved", "rejected", "expired"]


class TraceEvent(TypedDict):
    node: str
    event_type: str
    message: str
    metadata: dict[str, Any]


class AgentState(TypedDict):
    ticket_id: str
    user_message: str

    category: Optional[Category]
    intent: Optional[str]
    risk_level: Optional[RiskLevel]
    needs_human_review: bool

    confidence: Optional[float]
    decision_summary: Optional[str]

    approval_status: ApprovalStatus
    approval_id: Optional[str]
    approval_notes: Optional[str]
    approved_by: Optional[str]

    workflow_path: list[str]
    trace_events: list[TraceEvent]

    errors: list[str]
    final_response: Optional[str]