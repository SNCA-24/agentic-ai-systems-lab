from typing import Any

from openai import OpenAI
from langgraph.types import interrupt

from app.config import CLASSIFIER_MODE, OPENAI_MODEL
from app.schemas import TicketClassification
from app.state import AgentState, TraceEvent
from app.action_store import build_idempotency_key
from app.tools import (
    get_technical_diagnostics,
    lookup_billing_record,
    preview_high_risk_action,
)
from app.write_tools import execute_approved_high_risk_action


client = OpenAI()

CLASSIFIER_INSTRUCTIONS = """
You classify enterprise support tickets into a strict schema.

Categories:
- billing: charges, invoices, payment issues, subscription billing, duplicate charges
- refund: explicit refund requests where the main user intent is money back
- technical: bugs, crashes, login issues, upload failures, account access, account restore/delete requests, admin access changes, permissions
- general: how-to questions or simple product questions
- unknown: only use when the request is genuinely unclear or cannot be mapped to the categories above

Risk rules:
- high: account deletion/restoration, admin access changes, permission changes, security incidents, data loss, compliance/legal issues, irreversible actions, large refunds, or large financial actions
- medium: normal billing issues, duplicate charges, standard refund requests, login/account access issues, technical bugs affecting usage
- low: simple how-to questions or general product questions

Human review rules:
- needs_human_review must be true when risk_level is high
- needs_human_review must be false when risk_level is low or medium
- normal duplicate-charge, billing, refund, login, crash, upload, and product-help tickets do not need human review unless they are high-risk by the rules above

Important examples:
- "My app crashes whenever I upload a PDF" => category=technical, risk_level=medium, needs_human_review=false
- "I was charged twice for my subscription" => category=billing, risk_level=medium, needs_human_review=false
- "Our admin deleted 80 users. Restore them immediately" => category=technical, risk_level=high, needs_human_review=true
- "Please give this employee admin access immediately" => category=technical, risk_level=high, needs_human_review=true

Return only the structured classification.
"""


def add_trace_event(
    trace_events: list[TraceEvent],
    node: str,
    event_type: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> list[TraceEvent]:
    return trace_events + [
        {
            "node": node,
            "event_type": event_type,
            "message": message,
            "metadata": metadata or {},
        }
    ]


def validate_input(state: AgentState) -> dict:
    
    path = state["workflow_path"] + ["validate_input"]
    message = state["user_message"].strip()

    if not message:
        return {
            "workflow_path": path,
            "trace_events": add_trace_event(
                state["trace_events"],
                node="validate_input",
                event_type="validation_failed",
                message="Ticket validation failed because user_message was empty.",
                metadata={"ticket_id": state["ticket_id"]},
            ),
            "errors": state["errors"] + ["Empty user message"],
            "category": "unknown",
            "intent": "empty_message",
            "risk_level": "low",
            "needs_human_review": False,
            "confidence": 1.0,
            "decision_summary": "User message was empty.",
            
        }

    return {
        "workflow_path": path,
        "trace_events": add_trace_event(
            state["trace_events"],
            node="validate_input",
            event_type="validation_passed",
            message="Ticket input validation passed.",
            metadata={"ticket_id": state["ticket_id"]},
        ),
    }



def classify_ticket_mock(state: AgentState, path: list[str]) -> dict:
    """
    Local deterministic classifier for development and evaluation.
    This avoids paid LLM calls during frequent local runs.
    """
    message = state["user_message"].lower()

    high_risk_keywords = [
        "delete all",
        "deleted 80",
        "80 users",
        "restore them",
        "restore users",
        "admin access",
        "permission change",
        "large refund",
        "$2000",
        "$2,000",
        "security incident",
        "data loss",
    ]

    if any(keyword in message for keyword in high_risk_keywords):
        return {
            "workflow_path": path,
            "trace_events": add_trace_event(
                state["trace_events"],
                node="classify_ticket",
                event_type="mock_classification_completed",
                message="Mock ticket classification completed.",
                metadata={
                    "category": "technical",
                    "intent": "high_risk_account_or_financial_action",
                    "risk_level": "high",
                    "needs_human_review": True,
                    "confidence": 0.99,
                    "classifier_mode": CLASSIFIER_MODE,
                },
            ),
            "category": "technical",
            "intent": "high_risk_account_or_financial_action",
            "risk_level": "high",
            "needs_human_review": True,
            "confidence": 0.99,
            "decision_summary": "Mock classifier detected a high-risk account, permission, security, or financial action.",
        }

    if "refund" in message:
        return {
            "workflow_path": path,
            "trace_events": add_trace_event(
                state["trace_events"],
                node="classify_ticket",
                event_type="mock_classification_completed",
                message="Mock ticket classification completed.",
                metadata={
                    "category": "refund",
                    "intent": "standard_refund_request",
                    "risk_level": "medium",
                    "needs_human_review": False,
                    "confidence": 0.95,
                    "classifier_mode": CLASSIFIER_MODE,
                },
            ),
            "category": "refund",
            "intent": "standard_refund_request",
            "risk_level": "medium",
            "needs_human_review": False,
            "confidence": 0.95,
            "decision_summary": "Mock classifier detected a standard refund request.",
        }

    if "charged" in message or "charge" in message or "invoice" in message or "billing" in message:
        return {
            "workflow_path": path,
            "trace_events": add_trace_event(
                state["trace_events"],
                node="classify_ticket",
                event_type="mock_classification_completed",
                message="Mock ticket classification completed.",
                metadata={
                    "category": "billing",
                    "intent": "billing_or_duplicate_charge_issue",
                    "risk_level": "medium",
                    "needs_human_review": False,
                    "confidence": 0.95,
                    "classifier_mode": CLASSIFIER_MODE,
                },
            ),
            "category": "billing",
            "intent": "billing_or_duplicate_charge_issue",
            "risk_level": "medium",
            "needs_human_review": False,
            "confidence": 0.95,
            "decision_summary": "Mock classifier detected a billing or duplicate-charge issue.",
        }

    if (
        "crash" in message
        or "bug" in message
        or "upload" in message
        or "login" in message
        or "locked" in message
    ):
        return {
            "workflow_path": path,
            "trace_events": add_trace_event(
                state["trace_events"],
                node="classify_ticket",
                event_type="mock_classification_completed",
                message="Mock ticket classification completed.",
                metadata={
                    "category": "technical",
                    "intent": "technical_issue",
                    "risk_level": "medium",
                    "needs_human_review": False,
                    "confidence": 0.95,
                    "classifier_mode": CLASSIFIER_MODE,
                },
            ),
            "category": "technical",
            "intent": "technical_issue",
            "risk_level": "medium",
            "needs_human_review": False,
            "confidence": 0.95,
            "decision_summary": "Mock classifier detected a technical support issue.",
        }

    return {
        "workflow_path": path,
        "trace_events": add_trace_event(
            state["trace_events"],
            node="classify_ticket",
            event_type="mock_classification_completed",
            message="Mock ticket classification completed.",
            metadata={
                "category": "general",
                "intent": "general_support_question",
                "risk_level": "low",
                "needs_human_review": False,
                "confidence": 0.95,
                "classifier_mode": CLASSIFIER_MODE,
            },
        ),
        "category": "general",
        "intent": "general_support_question",
        "risk_level": "low",
        "needs_human_review": False,
        "confidence": 0.95,
        "decision_summary": "Mock classifier detected a general support question.",
    }

def classify_ticket(state: AgentState) -> dict:

    path = state["workflow_path"] + ["classify_ticket"]

    if CLASSIFIER_MODE == "mock":
        return classify_ticket_mock(state, path)

    try:
        response = client.responses.parse(
            model=OPENAI_MODEL,
            input=[
                {"role": "system", "content": CLASSIFIER_INSTRUCTIONS},
                {"role": "user", "content": state["user_message"]},
            ],
            text_format=TicketClassification,
        )

        classification = response.output_parsed

        return {
            "workflow_path": path,
            "trace_events": add_trace_event(
                state["trace_events"],
                node="classify_ticket",
                event_type="llm_classification_completed",
                message="LLM ticket classification completed.",
                metadata={
                    "category": classification.category,
                    "intent": classification.intent,
                    "risk_level": classification.risk_level,
                    "needs_human_review": classification.needs_human_review,
                    "confidence": classification.confidence,
                    "classifier_mode": CLASSIFIER_MODE,
                    "model": OPENAI_MODEL,
                },
            ),
            "category": classification.category,
            "intent": classification.intent,
            "risk_level": classification.risk_level,
            "needs_human_review": classification.needs_human_review,
            "confidence": classification.confidence,
            "decision_summary": classification.decision_summary,
            
        }

    except Exception as error:
        return {
            "workflow_path": path,
            "trace_events": add_trace_event(
                state["trace_events"],
                node="classify_ticket",
                event_type="classification_failed",
                message="Classification failed and was routed conservatively.",
                metadata={
                    "error": str(error),
                    "fallback_category": "unknown",
                    "fallback_risk_level": "medium",
                    "fallback_needs_human_review": True,
                    "classifier_mode": CLASSIFIER_MODE,
                    "model": OPENAI_MODEL,
                },
            ),
            "errors": state["errors"] + [f"Classification failed: {str(error)}"],
            "category": "unknown",
            "intent": "classification_failed",
            "risk_level": "medium",
            "needs_human_review": True,
            "confidence": 0.0,
            "decision_summary": "Classification failed; routed for human review.",
            
        }


def billing_node(state: AgentState) -> dict:
    tool_result = lookup_billing_record(ticket_id=state["ticket_id"])

    return {
        "workflow_path": state["workflow_path"] + ["billing_node"],
        "tool_results": state["tool_results"] + [tool_result.model_dump()],
        "trace_events": add_trace_event(
            state["trace_events"],
            node="billing_node",
            event_type="route_completed",
            message="Ticket routed to billing workflow and read-only billing evidence was collected.",
            metadata={
                "category": state["category"],
                "intent": state["intent"],
                "risk_level": state["risk_level"],
                "tool_name": tool_result.tool_name,
                "tool_status": tool_result.status,
                "tool_type": tool_result.result.get("tool_type"),
            },
        ),
        "final_response": (
            "This looks like a billing-related request. "
            "A read-only billing lookup was completed. "
            "Next step: review billing evidence and refund policy before taking action."
        ),
    }


def technical_node(state: AgentState) -> dict:
    tool_result = get_technical_diagnostics(ticket_id=state["ticket_id"])

    return {
        "workflow_path": state["workflow_path"] + ["technical_node"],
        "tool_results": state["tool_results"] + [tool_result.model_dump()],
        "trace_events": add_trace_event(
            state["trace_events"],
            node="technical_node",
            event_type="route_completed",
            message="Ticket routed to technical workflow and diagnostic checklist was generated.",
            metadata={
                "category": state["category"],
                "intent": state["intent"],
                "risk_level": state["risk_level"],
                "tool_name": tool_result.tool_name,
                "tool_status": tool_result.status,
                "tool_type": tool_result.result.get("tool_type"),
            },
        ),
        "final_response": (
            "This looks like a technical issue. "
            "A read-only diagnostics checklist was generated. "
            "Next step: collect app version, device/OS, logs, screenshots, and reproduction steps."
        ),
    }


def general_node(state: AgentState) -> dict:
    return {
        "workflow_path": state["workflow_path"] + ["general_node"],
        "trace_events": add_trace_event(
            state["trace_events"],
            node="general_node",
            event_type="route_completed",
            message="Ticket routed to general support workflow.",
            metadata={
                "category": state["category"],
                "intent": state["intent"],
                "risk_level": state["risk_level"],
            },
        ),
        "final_response": (
            "This looks like a general support request. "
            "Next step: answer directly or search the help center."
        ),
    }


def high_risk_review_node(state: AgentState) -> dict:
    tool_result = preview_high_risk_action(
        ticket_id=state["ticket_id"],
        intent=state["intent"],
    )

    return {
        "workflow_path": state["workflow_path"] + ["high_risk_review_node"],
        "approval_status": "pending",
        "tool_results": state["tool_results"] + [tool_result.model_dump()],
        "trace_events": add_trace_event(
            state["trace_events"],
            node="high_risk_review_node",
            event_type="human_review_required",
            message="High-risk ticket routed to human review and action preview was generated.",
            metadata={
                "category": state["category"],
                "intent": state["intent"],
                "risk_level": state["risk_level"],
                "needs_human_review": state["needs_human_review"],
                "approval_status": "pending",
                "tool_name": tool_result.tool_name,
                "tool_status": tool_result.status,
                "tool_type": tool_result.result.get("tool_type"),
                "write_action_executed": tool_result.result.get("write_action_executed"),
            },
        ),
        "final_response": (
            "This request appears high-risk and has been marked as pending human approval. "
            "A preview-only action review was generated, and no write action has been executed."
        ),
    }


# Interrupt-style human approval node for experimental HITL workflows
def human_approval_interrupt_node(state: AgentState) -> dict:
    """
    True interrupt-style human approval node for experimental HITL workflows.

    On the first pass, this node pauses graph execution using LangGraph interrupt().
    On resume, the approval decision payload is returned from interrupt() and used
    to update graph state before routing to approved/rejected/blocked nodes.
    """
    approval_payload = interrupt(
        {
            "ticket_id": state["ticket_id"],
            "approval_status": "pending",
            "approval_required": True,
            "reason": "High-risk ticket requires human approval before any write action can execute.",
            "category": state["category"],
            "intent": state["intent"],
            "risk_level": state["risk_level"],
            "decision_summary": state["decision_summary"],
            "action_preview": state["tool_results"][-1] if state["tool_results"] else None,
        }
    )

    approved = bool(approval_payload.get("approved", False))
    approval_status = "approved" if approved else "rejected"

    return {
        "workflow_path": state["workflow_path"] + ["human_approval_interrupt_node"],
        "approval_status": approval_status,
        "approval_id": approval_payload.get("approval_id"),
        "approved_by": approval_payload.get("approved_by"),
        "approval_notes": approval_payload.get("approval_notes"),
        "trace_events": add_trace_event(
            state["trace_events"],
            node="human_approval_interrupt_node",
            event_type="human_approval_interrupt_resumed",
            message="Interruptible workflow resumed with a human approval decision.",
            metadata={
                "ticket_id": state["ticket_id"],
                "approval_status": approval_status,
                "approval_id": approval_payload.get("approval_id"),
                "approved_by": approval_payload.get("approved_by"),
            },
        ),
    }

def approval_approved_node(state: AgentState) -> dict:
    return {
        "workflow_path": state["workflow_path"] + ["approval_approved_node"],
        "approval_status": "approved",
        "trace_events": add_trace_event(
            state["trace_events"],
            node="approval_approved_node",
            event_type="approval_resume_approved",
            message="Approval decision was approved. Workflow will continue to approved action execution.",
            metadata={
                "ticket_id": state["ticket_id"],
                "approval_status": "approved",
                "approval_id": state["approval_id"],
                "approved_by": state["approved_by"],
            },
        ),
        "final_response": (
            "Human approval was recorded as approved. "
            "The workflow will continue to the approved action execution path."
        ),
    }


def execute_approved_action_node(state: AgentState) -> dict:
    action_type = "simulated_high_risk_action"
    approval_id = state["approval_id"] or "missing_approval_id"
    idempotency_key = build_idempotency_key(
        ticket_id=state["ticket_id"],
        approval_id=approval_id,
        action_type=action_type,
    )

    tool_result = execute_approved_high_risk_action(
        ticket_id=state["ticket_id"],
        approval_id=approval_id,
        approved_by=state["approved_by"],
        idempotency_key=idempotency_key,
        action_type=action_type,
    )

    if tool_result.status == "success":
        final_response = (
            "Approved high-risk action was simulated successfully. "
            "The action execution was recorded with an idempotency key."
        )
    else:
        final_response = (
            "Approved high-risk action was not executed again because the idempotency key "
            "was already used. Returning the previously recorded execution result."
        )

    return {
        "workflow_path": state["workflow_path"] + ["execute_approved_action_node"],
        "tool_results": state["tool_results"] + [tool_result.model_dump()],
        "trace_events": add_trace_event(
            state["trace_events"],
            node="execute_approved_action_node",
            event_type="approved_write_tool_completed",
            message="Approved write-tool simulation completed with idempotency protection.",
            metadata={
                "ticket_id": state["ticket_id"],
                "approval_status": state["approval_status"],
                "approval_id": state["approval_id"],
                "approved_by": state["approved_by"],
                "tool_name": tool_result.tool_name,
                "tool_status": tool_result.status,
                "idempotency_key": idempotency_key,
                "write_action_executed": tool_result.result.get("write_action_executed"),
                "duplicate_prevented": tool_result.result.get("duplicate_prevented"),
                "tool_type": tool_result.result.get("tool_type"),
            },
        ),
        "final_response": final_response,
    }


def approval_rejected_node(state: AgentState) -> dict:
    return {
        "workflow_path": state["workflow_path"] + ["approval_rejected_node"],
        "approval_status": "rejected",
        "trace_events": add_trace_event(
            state["trace_events"],
            node="approval_rejected_node",
            event_type="approval_resume_rejected",
            message="Approval decision was rejected. Workflow is safely blocked.",
            metadata={
                "ticket_id": state["ticket_id"],
                "approval_status": "rejected",
                "approval_id": state["approval_id"],
                "approved_by": state["approved_by"],
            },
        ),
        "final_response": (
            "Human approval was rejected. "
            "The high-risk action remains blocked and no write action has been executed."
        ),
    }


def approval_blocked_node(state: AgentState) -> dict:
    return {
        "workflow_path": state["workflow_path"] + ["approval_blocked_node"],
        "trace_events": add_trace_event(
            state["trace_events"],
            node="approval_blocked_node",
            event_type="approval_resume_blocked",
            message="Approval decision is missing, pending, or expired. Workflow remains blocked.",
            metadata={
                "ticket_id": state["ticket_id"],
                "approval_status": state["approval_status"],
                "approval_id": state["approval_id"],
                "approved_by": state["approved_by"],
            },
        ),
        "errors": state["errors"] + [
            f"Cannot resume workflow because approval_status={state['approval_status']}."
        ],
        "final_response": (
            "The workflow cannot resume because approval is missing, pending, or expired. "
            "No write action has been executed."
        ),
    }

def error_node(state: AgentState) -> dict:
    return {
        "workflow_path": state["workflow_path"] + ["error_node"],
        "trace_events": add_trace_event(
            state["trace_events"],
            node="error_node",
            event_type="workflow_error",
            message="Ticket routed to error workflow.",
            metadata={"errors": state["errors"]},
        ),
        "final_response": f"Could not process ticket. Errors: {state['errors']}",
    }