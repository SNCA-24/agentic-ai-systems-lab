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