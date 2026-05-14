from typing import Literal, Optional
from typing_extensions import TypedDict


Category = Literal["billing", "refund", "technical", "general", "unknown"]
RiskLevel = Literal["low", "medium", "high"]


class AgentState(TypedDict):
    ticket_id: str
    user_message: str

    category: Optional[Category]
    intent: Optional[str]
    risk_level: Optional[RiskLevel]
    needs_human_review: bool

    confidence: Optional[float]
    decision_summary: Optional[str]

    workflow_path: list[str]

    errors: list[str]
    final_response: Optional[str]