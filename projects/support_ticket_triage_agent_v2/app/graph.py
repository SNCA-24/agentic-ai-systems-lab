from langgraph.graph import StateGraph, START, END

from app.state import AgentState
from app.nodes import (
    validate_input,
    classify_ticket,
    billing_node,
    technical_node,
    general_node,
    high_risk_review_node,
    error_node,
)


def route_after_validation(state: AgentState) -> str:
    if state["errors"]:
        return "error"

    return "classify"


def route_after_classification(state: AgentState) -> str:
    if state["needs_human_review"] or state["risk_level"] == "high":
        return "high_risk"

    if state["category"] in {"billing", "refund"}:
        return "billing"

    if state["category"] == "technical":
        return "technical"

    if state["category"] == "general":
        return "general"

    return "error"


builder = StateGraph(AgentState)

builder.add_node("validate_input", validate_input)
builder.add_node("classify_ticket", classify_ticket)
builder.add_node("billing_node", billing_node)
builder.add_node("technical_node", technical_node)
builder.add_node("general_node", general_node)
builder.add_node("high_risk_review_node", high_risk_review_node)
builder.add_node("error_node", error_node)

builder.add_edge(START, "validate_input")

builder.add_conditional_edges(
    "validate_input",
    route_after_validation,
    {
        "classify": "classify_ticket",
        "error": "error_node",
    },
)

builder.add_conditional_edges(
    "classify_ticket",
    route_after_classification,
    {
        "billing": "billing_node",
        "technical": "technical_node",
        "general": "general_node",
        "high_risk": "high_risk_review_node",
        "error": "error_node",
    },
)

builder.add_edge("billing_node", END)
builder.add_edge("technical_node", END)
builder.add_edge("general_node", END)
builder.add_edge("high_risk_review_node", END)
builder.add_edge("error_node", END)

ticket_graph = builder.compile()