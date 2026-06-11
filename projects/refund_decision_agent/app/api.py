from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Query

from app.graph import create_initial_state, refund_decision_graph
from app.schemas import RefundDecisionRequest, RefundDecisionResponse


app = FastAPI(title="Refund Decision Agent API")


@app.post(
    "/refunds/decide",
    response_model=RefundDecisionResponse,
    response_model_exclude_unset=True,
)
def decide_refund(
    request: RefundDecisionRequest,
    debug: bool | None = Query(
        default=None,
        description="Expose internal workflow details in the response.",
    ),
) -> dict[str, Any]:
    effective_debug = request.debug or bool(debug)
    initial_state = create_initial_state(
        request_id=request.request_id,
        customer_id=request.customer_id,
        user_message=request.user_message,
        debug=effective_debug,
        classifier_mode="mock",
    )
    result = refund_decision_graph.invoke(initial_state)
    response = RefundDecisionResponse(
        request_id=result["request_id"],
        customer_id=result["customer_id"],
        refund_eligible=result.get("refund_eligible"),
        refund_amount=result.get("refund_amount"),
        risk_level=result.get("risk_level"),
        needs_human_review=result["needs_human_review"],
        decision_reason=result.get("decision_reason"),
        policy_basis=result.get("policy_basis", []),
        evidence_summary=result.get("evidence_summary"),
        final_response=result.get("final_response"),
        status=result["status"],
        workflow_path=result.get("workflow_path", []),
        trace_events=result.get("trace_events", []),
        errors=result.get("errors", []),
        debug=effective_debug,
    )
    return response.public_dump()
