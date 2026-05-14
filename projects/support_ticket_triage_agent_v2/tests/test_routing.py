from app.graph import ticket_graph
from app.state import AgentState


def run_graph(message: str, ticket_id: str = "TEST-ROUTE-001") -> AgentState:
    initial_state: AgentState = {
        "ticket_id": ticket_id,
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
        "workflow_path": [],
        "trace_events": [],
        "errors": [],
        "final_response": None,
    }

    return ticket_graph.invoke(initial_state)


def test_billing_ticket_routes_to_billing_node():
    result = run_graph("I was charged twice for my subscription.")

    assert result["category"] == "billing"
    assert result["risk_level"] == "medium"
    assert result["needs_human_review"] is False
    assert result["approval_status"] == "not_required"
    assert result["workflow_path"] == [
        "validate_input",
        "classify_ticket",
        "billing_node",
    ]


def test_technical_ticket_routes_to_technical_node():
    result = run_graph("My app keeps crashing whenever I upload a PDF.")

    assert result["category"] == "technical"
    assert result["risk_level"] == "medium"
    assert result["needs_human_review"] is False
    assert result["approval_status"] == "not_required"
    assert result["workflow_path"] == [
        "validate_input",
        "classify_ticket",
        "technical_node",
    ]


def test_high_risk_ticket_routes_to_review_node():
    result = run_graph("Our admin deleted 80 users. Can you restore them immediately?")

    assert result["category"] == "technical"
    assert result["risk_level"] == "high"
    assert result["needs_human_review"] is True
    assert result["approval_status"] == "pending"
    assert result["workflow_path"] == [
        "validate_input",
        "classify_ticket",
        "high_risk_review_node",
    ]
    assert result["final_response"].startswith("This request appears high-risk")
    assert "pending human approval" in result["final_response"]


def test_general_ticket_routes_to_general_node():
    result = run_graph("How do I change my profile picture?")

    assert result["category"] == "general"
    assert result["risk_level"] == "low"
    assert result["needs_human_review"] is False
    assert result["approval_status"] == "not_required"
    assert result["workflow_path"] == [
        "validate_input",
        "classify_ticket",
        "general_node",
    ]


def test_empty_ticket_routes_to_error_node():
    result = run_graph("   ")

    assert result["category"] == "unknown"
    assert result["intent"] == "empty_message"
    assert result["approval_status"] == "not_required"
    assert result["workflow_path"] == [
        "validate_input",
        "error_node",
    ]
    assert result["errors"] == ["Empty user message"]
