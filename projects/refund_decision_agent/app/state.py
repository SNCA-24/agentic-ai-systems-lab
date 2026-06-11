from __future__ import annotations

from typing import Any, Literal

from typing_extensions import TypedDict


class RefundDecisionState(TypedDict, total=False):
    request_id: str
    customer_id: str
    user_message: str
    debug: bool
    classifier_mode: str

    intent: str | None
    category: str | None
    risk_level: Literal["low", "medium", "high"] | None

    retrieved_policy_docs: list[dict[str, Any]]
    billing_evidence: dict[str, Any]
    customer_context: dict[str, Any]

    refund_eligible: bool | None
    refund_amount: float | None
    needs_human_review: bool
    decision_reason: str | None
    policy_basis: list[str]
    evidence_summary: str | None
    status: Literal["eligible", "ineligible", "human_review", "escalated"] | None
    final_node: str | None

    workflow_path: list[str]
    trace_events: list[dict[str, Any]]
    errors: list[str]
    final_response: str | None

    persistence_status: Literal["persisted", "failed"] | None
    persistence_record: dict[str, Any] | None
