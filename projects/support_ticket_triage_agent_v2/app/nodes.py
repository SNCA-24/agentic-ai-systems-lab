from typing import Any

from openai import OpenAI

from app.config import CLASSIFIER_MODE, OPENAI_MODEL
from app.schemas import TicketClassification
from app.state import AgentState, TraceEvent


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
    return {
        "workflow_path": state["workflow_path"] + ["billing_node"],
        "trace_events": add_trace_event(
            state["trace_events"],
            node="billing_node",
            event_type="route_completed",
            message="Ticket routed to billing workflow.",
            metadata={
                "category": state["category"],
                "intent": state["intent"],
                "risk_level": state["risk_level"],
            },
        ),
        "final_response": (
            "This looks like a billing-related request. "
            "Next step: check billing records and refund policy."
        ),
    }


def technical_node(state: AgentState) -> dict:
    return {
        "workflow_path": state["workflow_path"] + ["technical_node"],
        "trace_events": add_trace_event(
            state["trace_events"],
            node="technical_node",
            event_type="route_completed",
            message="Ticket routed to technical workflow.",
            metadata={
                "category": state["category"],
                "intent": state["intent"],
                "risk_level": state["risk_level"],
            },
        ),
        "final_response": (
            "This looks like a technical issue. "
            "Next step: collect diagnostics such as app version, device, logs, and error details."
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
    return {
        "workflow_path": state["workflow_path"] + ["high_risk_review_node"],
        "approval_status": "pending",
        "trace_events": add_trace_event(
            state["trace_events"],
            node="high_risk_review_node",
            event_type="human_review_required",
            message="High-risk ticket routed to human review.",
            metadata={
                "category": state["category"],
                "intent": state["intent"],
                "risk_level": state["risk_level"],
                "needs_human_review": state["needs_human_review"],
                "approval_status": "pending",
            },
        ),
        "final_response": (
            "This request appears high-risk and has been marked as pending human approval. "
            "No write action has been executed."
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
            message="Approval decision was approved. Workflow is ready for the approved action path.",
            metadata={
                "ticket_id": state["ticket_id"],
                "approval_status": "approved",
                "approval_id": state["approval_id"],
                "approved_by": state["approved_by"],
            },
        ),
        "final_response": (
            "Human approval was recorded as approved. "
            "The workflow is ready to continue to the approved action path. "
            "No write action has been executed in this version."
        ),
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