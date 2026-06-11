from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.nodes import (
    classify_refund_request_node,
    decide_refund_eligibility_node,
    eligible_response_node,
    escalation_response_node,
    human_review_required_node,
    ineligible_response_node,
    lookup_billing_evidence_node,
    persist_decision_node,
    retrieve_policy_context_node,
    validate_input_node,
)
from app.state import RefundDecisionState


def create_initial_state(
    *,
    request_id: str,
    customer_id: str,
    user_message: str,
    debug: bool = False,
    classifier_mode: str = "mock",
) -> RefundDecisionState:
    return {
        "request_id": request_id,
        "customer_id": customer_id,
        "user_message": user_message,
        "debug": debug,
        "classifier_mode": classifier_mode,
        "intent": None,
        "category": None,
        "risk_level": None,
        "retrieved_policy_docs": [],
        "billing_evidence": {},
        "customer_context": {},
        "refund_eligible": None,
        "refund_amount": None,
        "needs_human_review": False,
        "decision_reason": None,
        "policy_basis": [],
        "evidence_summary": None,
        "status": None,
        "final_node": None,
        "workflow_path": [],
        "trace_events": [],
        "errors": [],
        "final_response": None,
        "persistence_status": None,
        "persistence_record": None,
    }


def route_after_linear_node(state: RefundDecisionState) -> str:
    if state.get("status") == "escalated" or bool(state.get("errors")):
        return "escalate"
    return "continue"


def route_after_decision(state: RefundDecisionState) -> str:
    status = state.get("status")
    refund_eligible = state.get("refund_eligible")

    if status == "eligible" and refund_eligible is True and not state.get("needs_human_review", False):
        return "eligible"
    if status == "ineligible" and refund_eligible is False:
        return "ineligible"
    if status == "human_review":
        return "human_review"
    return "escalate"


def route_after_response_node(state: RefundDecisionState) -> str:
    if state.get("status") == "escalated" or bool(state.get("errors")):
        return "escalate"
    return "persist"


builder = StateGraph(RefundDecisionState)

builder.add_node("validate_input_node", validate_input_node)
builder.add_node("classify_refund_request_node", classify_refund_request_node)
builder.add_node("retrieve_policy_context_node", retrieve_policy_context_node)
builder.add_node("lookup_billing_evidence_node", lookup_billing_evidence_node)
builder.add_node("decide_refund_eligibility_node", decide_refund_eligibility_node)
builder.add_node("eligible_response_node", eligible_response_node)
builder.add_node("ineligible_response_node", ineligible_response_node)
builder.add_node("human_review_required_node", human_review_required_node)
builder.add_node("escalation_response_node", escalation_response_node)
builder.add_node("persist_decision_node", persist_decision_node)

builder.add_edge(START, "validate_input_node")

builder.add_conditional_edges(
    "validate_input_node",
    route_after_linear_node,
    {
        "continue": "classify_refund_request_node",
        "escalate": "escalation_response_node",
    },
)
builder.add_conditional_edges(
    "classify_refund_request_node",
    route_after_linear_node,
    {
        "continue": "retrieve_policy_context_node",
        "escalate": "escalation_response_node",
    },
)
builder.add_conditional_edges(
    "retrieve_policy_context_node",
    route_after_linear_node,
    {
        "continue": "lookup_billing_evidence_node",
        "escalate": "escalation_response_node",
    },
)
builder.add_conditional_edges(
    "lookup_billing_evidence_node",
    route_after_linear_node,
    {
        "continue": "decide_refund_eligibility_node",
        "escalate": "escalation_response_node",
    },
)
builder.add_conditional_edges(
    "decide_refund_eligibility_node",
    route_after_decision,
    {
        "eligible": "eligible_response_node",
        "ineligible": "ineligible_response_node",
        "human_review": "human_review_required_node",
        "escalate": "escalation_response_node",
    },
)

builder.add_conditional_edges(
    "eligible_response_node",
    route_after_response_node,
    {
        "persist": "persist_decision_node",
        "escalate": "escalation_response_node",
    },
)
builder.add_conditional_edges(
    "ineligible_response_node",
    route_after_response_node,
    {
        "persist": "persist_decision_node",
        "escalate": "escalation_response_node",
    },
)
builder.add_conditional_edges(
    "human_review_required_node",
    route_after_response_node,
    {
        "persist": "persist_decision_node",
        "escalate": "escalation_response_node",
    },
)
builder.add_edge("escalation_response_node", "persist_decision_node")
builder.add_edge("persist_decision_node", END)

refund_decision_graph = builder.compile()
