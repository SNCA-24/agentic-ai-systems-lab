from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_non_blank(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned


class StrictRefundModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RefundDecisionRequest(StrictRefundModel):
    request_id: str = Field(description="Unique refund decision request identifier.")
    customer_id: str = Field(description="Synthetic customer identifier.")
    user_message: str = Field(description="Raw customer message describing the refund request.")
    debug: bool = False

    @field_validator("request_id", "customer_id", "user_message", mode="before")
    @classmethod
    def _strip_required_text(cls, value: Any, info) -> str:
        return _validate_non_blank(value, info.field_name)


class RefundIntentClassification(StrictRefundModel):
    intent: str = Field(description="Refund-related intent label.")
    category: str = Field(description="High-level request category.")
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high"]

    @field_validator("intent", "category", mode="before")
    @classmethod
    def _strip_text(cls, value: Any, info) -> str:
        return _validate_non_blank(value, info.field_name)


class RetrievedPolicyDocument(StrictRefundModel):
    source: str = Field(description="Source file or section label.")
    section_title: str = Field(description="Section title within the policy source.")
    section_ref: str = Field(description="Stable section reference or anchor.")
    score: float = Field(ge=0.0, le=1.0)
    content: str = Field(description="Relevant policy excerpt.")

    @field_validator("source", "section_title", "section_ref", "content", mode="before")
    @classmethod
    def _strip_text(cls, value: Any, info) -> str:
        return _validate_non_blank(value, info.field_name)


class BillingLookupResult(StrictRefundModel):
    customer_found: bool
    subscription_status: str | None = Field(
        default=None,
        description="Current subscription status.",
    )
    cancellation_timestamp: str | None = Field(
        default=None,
        description="Cancellation timestamp if the subscription has been canceled.",
    )
    recent_charges: list[dict[str, Any]] = Field(default_factory=list)
    refund_history: list[dict[str, Any]] = Field(default_factory=list)
    conflict_flags: list[str] = Field(default_factory=list)

    @field_validator("subscription_status", "cancellation_timestamp", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: Any, info) -> str | None:
        if value is None:
            return None
        return _validate_non_blank(value, info.field_name)


class RefundEligibilityDecision(StrictRefundModel):
    refund_eligible: bool | None = None
    refund_amount: float | None = None
    risk_level: Literal["low", "medium", "high"]
    needs_human_review: bool
    decision_reason: str
    policy_basis: list[str] = Field(default_factory=list)
    evidence_summary: str | None = None
    status: Literal["eligible", "ineligible", "human_review", "escalated"]

    @field_validator("decision_reason", "evidence_summary", "status", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: Any, info) -> str | None:
        if value is None:
            return None
        return _validate_non_blank(value, info.field_name)


class TraceEvent(StrictRefundModel):
    node: str = Field(description="Workflow node name that emitted the event.")
    event_type: str = Field(description="Stable event type label.")
    message: str = Field(description="Human-readable trace message.")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("node", "event_type", "message", mode="before")
    @classmethod
    def _strip_text(cls, value: Any, info) -> str:
        return _validate_non_blank(value, info.field_name)


class RefundDecisionResponse(StrictRefundModel):
    request_id: str
    customer_id: str
    refund_eligible: bool | None = None
    refund_amount: float | None = None
    risk_level: Literal["low", "medium", "high"] | None = None
    needs_human_review: bool
    decision_reason: str | None = None
    policy_basis: list[str] = Field(default_factory=list)
    evidence_summary: str | None = None
    final_response: str | None = None
    status: Literal["eligible", "ineligible", "human_review", "escalated"]
    workflow_path: list[str] = Field(default_factory=list)
    trace_events: list[TraceEvent] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    debug: bool = False

    @field_validator("request_id", "customer_id", mode="before")
    @classmethod
    def _strip_required_text(cls, value: Any, info) -> str:
        return _validate_non_blank(value, info.field_name)

    @field_validator("decision_reason", "evidence_summary", "final_response", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: Any, info) -> str | None:
        if value is None:
            return None
        return _validate_non_blank(value, info.field_name)

    def public_dump(self) -> dict[str, Any]:
        data = self.model_dump()
        if not self.debug:
            for key in ("workflow_path", "trace_events", "errors", "debug"):
                data.pop(key, None)
        return data


class DecisionRecord(StrictRefundModel):
    request_id: str
    customer_id: str
    refund_eligible: bool | None = None
    refund_amount: float | None = None
    risk_level: Literal["low", "medium", "high"] | None = None
    needs_human_review: bool
    final_node: str
    status: Literal["eligible", "ineligible", "human_review", "escalated"]
    decision_reason: str | None = None
    policy_basis: list[str] = Field(default_factory=list)
    evidence_summary: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("request_id", "customer_id", "final_node", mode="before")
    @classmethod
    def _strip_required_text(cls, value: Any, info) -> str:
        return _validate_non_blank(value, info.field_name)
