from typing import Literal
from pydantic import BaseModel, Field


class TicketClassification(BaseModel):
    category: Literal["billing", "refund", "technical", "general", "unknown"]
    intent: str = Field(
        description="Specific intent, such as duplicate_charge_refund, pdf_upload_crash, bulk_user_restore_request"
    )
    risk_level: Literal["low", "medium", "high"]
    needs_human_review: bool
    confidence: float = Field(ge=0.0, le=1.0)
    decision_summary: str = Field(
        description="Short factual summary. Do not include hidden reasoning."
    )


class TriageRequest(BaseModel):
    ticket_id: str = Field(description="Unique ticket identifier.")
    user_message: str = Field(description="Raw support ticket message submitted by the user.")


class TriageResponse(BaseModel):
    ticket_id: str
    category: Literal["billing", "refund", "technical", "general", "unknown"]
    intent: str
    risk_level: Literal["low", "medium", "high"]
    needs_human_review: bool
    approval_status: Literal["not_required", "pending", "approved", "rejected", "expired"]
    confidence: float | None
    decision_summary: str | None
    workflow_path: list[str]
    trace_events_count: int
    final_response: str | None
    errors: list[str]