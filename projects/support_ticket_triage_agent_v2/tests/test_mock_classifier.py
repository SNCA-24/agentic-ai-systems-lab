from app.nodes import classify_ticket_mock
from app.state import AgentState


def make_state(message: str) -> AgentState:
    return {
        "ticket_id": "TEST-001",
        "user_message": message,
        "category": None,
        "intent": None,
        "risk_level": None,
        "needs_human_review": False,
        "confidence": None,
        "decision_summary": None,
        "approval_status": "not_required",
        "approval_id": None,
        "approval_notes": None,
        "approved_by": None,
        "workflow_path": ["validate_input"],
        "trace_events": [],
        "errors": [],
        "final_response": None,
    }


def test_mock_classifier_routes_duplicate_charge_to_billing():
    state = make_state("I was charged twice for my subscription.")

    result = classify_ticket_mock(state, ["validate_input", "classify_ticket"])

    assert result["category"] == "billing"
    assert result["risk_level"] == "medium"
    assert result["needs_human_review"] is False
    assert result["intent"] == "billing_or_duplicate_charge_issue"
    assert result["workflow_path"] == ["validate_input", "classify_ticket"]
    assert len(result["trace_events"]) == 1
    assert result["trace_events"][0]["event_type"] == "mock_classification_completed"


def test_mock_classifier_routes_pdf_crash_to_technical():
    state = make_state("My app keeps crashing whenever I upload a PDF.")

    result = classify_ticket_mock(state, ["validate_input", "classify_ticket"])

    assert result["category"] == "technical"
    assert result["risk_level"] == "medium"
    assert result["needs_human_review"] is False
    assert result["intent"] == "technical_issue"


def test_mock_classifier_routes_deleted_users_to_high_risk():
    state = make_state("Our admin deleted 80 users. Can you restore them immediately?")

    result = classify_ticket_mock(state, ["validate_input", "classify_ticket"])

    assert result["category"] == "technical"
    assert result["risk_level"] == "high"
    assert result["needs_human_review"] is True
    assert result["intent"] == "high_risk_account_or_financial_action"


def test_mock_classifier_routes_profile_question_to_general():
    state = make_state("How do I change my profile picture?")

    result = classify_ticket_mock(state, ["validate_input", "classify_ticket"])

    assert result["category"] == "general"
    assert result["risk_level"] == "low"
    assert result["needs_human_review"] is False
    assert result["intent"] == "general_support_question"
