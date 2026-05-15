from langgraph.graph import StateGraph, START, END

from app.state import AgentState
from app.checkpointing import create_memory_checkpointer
from app.nodes import (
    validate_input,
    classify_ticket,
    billing_node,
    technical_node,
    general_node,
    high_risk_review_node,
    error_node,
    approval_approved_node,
    execute_approved_action_node,
    approval_rejected_node,
    approval_blocked_node,
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

def route_after_approval_status(state: AgentState) -> str:
    if state["approval_status"] == "approved":
        return "approved"

    if state["approval_status"] == "rejected":
        return "rejected"

    return "blocked"


def approval_resume_entry_node(state: AgentState) -> dict:
    return {
        "workflow_path": state["workflow_path"] + ["approval_resume_entry_node"],
    }

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

checkpointed_ticket_graph = builder.compile(
    checkpointer=create_memory_checkpointer(),
)

approval_resume_builder = StateGraph(AgentState)

approval_resume_builder.add_node("approval_resume_entry_node", approval_resume_entry_node)
approval_resume_builder.add_node("approval_approved_node", approval_approved_node)
approval_resume_builder.add_node("execute_approved_action_node", execute_approved_action_node)
approval_resume_builder.add_node("approval_rejected_node", approval_rejected_node)
approval_resume_builder.add_node("approval_blocked_node", approval_blocked_node)

approval_resume_builder.add_edge(START, "approval_resume_entry_node")

approval_resume_builder.add_conditional_edges(
    "approval_resume_entry_node",
    route_after_approval_status,
    {
        "approved": "approval_approved_node",
        "rejected": "approval_rejected_node",
        "blocked": "approval_blocked_node",
    },
)

approval_resume_builder.add_edge("approval_approved_node", "execute_approved_action_node")
approval_resume_builder.add_edge("execute_approved_action_node", END)
approval_resume_builder.add_edge("approval_rejected_node", END)
approval_resume_builder.add_edge("approval_blocked_node", END)

approval_resume_graph = approval_resume_builder.compile()

checkpointed_approval_resume_graph = approval_resume_builder.compile(
    checkpointer=create_memory_checkpointer(),
)