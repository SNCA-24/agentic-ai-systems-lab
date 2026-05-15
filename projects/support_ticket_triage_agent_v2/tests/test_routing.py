from app.graph import approval_resume_graph, ticket_graph
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

def run_approval_resume_graph(
    approval_status: str,
    approval_id: str | None = None,
    approved_by: str | None = None,
) -> AgentState:
    initial_state: AgentState = {
        "ticket_id": "TEST-APPROVAL-001",
        "user_message": "Resume high-risk workflow after approval decision.",
        "category": "technical",
        "intent": "high_risk_account_or_financial_action",
        "risk_level": "high",
        "needs_human_review": True,
        "confidence": 0.99,
        "decision_summary": "High-risk action pending approval.",
        "approval_status": approval_status,
        "approval_id": approval_id,
        "approval_notes": "Test approval decision.",
        "approved_by": approved_by,
        "workflow_path": [],
        "trace_events": [],
        "errors": [],
        "final_response": None,
    }

    return approval_resume_graph.invoke(initial_state)

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

def test_approval_resume_routes_approved_decision_to_approved_node():
    result = run_approval_resume_graph(
        approval_status="approved",
        approval_id="approval_123",
        approved_by="manager_001",
    )

    assert result["approval_status"] == "approved"
    assert result["workflow_path"] == [
        "approval_resume_entry_node",
        "approval_approved_node",
    ]
    assert result["trace_events"][-1]["event_type"] == "approval_resume_approved"
    assert "ready to continue" in result["final_response"]
    assert result["errors"] == []


def test_approval_resume_routes_rejected_decision_to_rejected_node():
    result = run_approval_resume_graph(
        approval_status="rejected",
        approval_id="approval_456",
        approved_by="manager_001",
    )

    assert result["approval_status"] == "rejected"
    assert result["workflow_path"] == [
        "approval_resume_entry_node",
        "approval_rejected_node",
    ]
    assert result["trace_events"][-1]["event_type"] == "approval_resume_rejected"
    assert "remains blocked" in result["final_response"]
    assert result["errors"] == []


def test_approval_resume_blocks_pending_decision():
    result = run_approval_resume_graph(approval_status="pending")

    assert result["approval_status"] == "pending"
    assert result["workflow_path"] == [
        "approval_resume_entry_node",
        "approval_blocked_node",
    ]
    assert result["trace_events"][-1]["event_type"] == "approval_resume_blocked"
    assert result["errors"] == ["Cannot resume workflow because approval_status=pending."]
    assert "cannot resume" in result["final_response"]