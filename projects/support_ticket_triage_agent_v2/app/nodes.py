from openai import OpenAI

from app.config import OPENAI_MODEL
from app.schemas import TicketClassification
from app.state import AgentState


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


def validate_input(state: AgentState) -> dict:
    
    path = state["workflow_path"] + ["validate_input"]
    message = state["user_message"].strip()

    if not message:
        return {
            "workflow_path": path,
            "errors": state["errors"] + ["Empty user message"],
            "category": "unknown",
            "intent": "empty_message",
            "risk_level": "low",
            "needs_human_review": False,
            "confidence": 1.0,
            "decision_summary": "User message was empty.",
            
        }

    return {"workflow_path": path}



def classify_ticket(state: AgentState) -> dict:

    path = state["workflow_path"] + ["classify_ticket"]
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
        "final_response": (
            "This looks like a billing-related request. "
            "Next step: check billing records and refund policy."
        )
    }


def technical_node(state: AgentState) -> dict:
    return {
        "workflow_path": state["workflow_path"] + ["technical_node"],
        "final_response": (
            "This looks like a technical issue. "
            "Next step: collect diagnostics such as app version, device, logs, and error details."
        )
    }


def general_node(state: AgentState) -> dict:
    return {
        "workflow_path": state["workflow_path"] + ["general_node"],
        "final_response": (
            "This looks like a general support request. "
            "Next step: answer directly or search the help center."
        )
    }


def high_risk_review_node(state: AgentState) -> dict:
    return {
        "workflow_path": state["workflow_path"] + ["high_risk_review_node"],
        "final_response": (
            "This request appears high-risk and requires human review before any action is taken. "
            "No write action has been executed."
        )
    }


def error_node(state: AgentState) -> dict:
    return {
        "workflow_path": state["workflow_path"] + ["error_node"],
        "final_response": f"Could not process ticket. Errors: {state['errors']}"
    }