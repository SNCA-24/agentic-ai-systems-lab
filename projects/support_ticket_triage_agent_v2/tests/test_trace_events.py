

from app.graph import ticket_graph
from app.state import AgentState


def run_graph(message: str, ticket_id: str = "TEST-TRACE-001") -> AgentState:
    initial_state: AgentState = {
        "ticket_id": ticket_id,
        "user_message": message,
        "category": None,
        "intent": None,
        "risk_level": None,
        "needs_human_review": False,
        "confidence": None,
        "decision_summary": None,
        "workflow_path": [],
        "trace_events": [],
        "errors": [],
        "final_response": None,
    }

    return ticket_graph.invoke(initial_state)


def event_types(result: AgentState) -> list[str]:
    return [event["event_type"] for event in result["trace_events"]]


def test_normal_ticket_records_three_trace_events():
    result = run_graph("My app keeps crashing whenever I upload a PDF.")

    assert len(result["trace_events"]) == 3
    assert event_types(result) == [
        "validation_passed",
        "mock_classification_completed",
        "route_completed",
    ]


def test_billing_ticket_final_trace_event_is_route_completed():
    result = run_graph("I was charged twice for my subscription.")

    final_event = result["trace_events"][-1]

    assert final_event["node"] == "billing_node"
    assert final_event["event_type"] == "route_completed"
    assert final_event["metadata"]["category"] == "billing"
    assert final_event["metadata"]["risk_level"] == "medium"


def test_high_risk_ticket_records_human_review_required_event():
    result = run_graph("Our admin deleted 80 users. Can you restore them immediately?")

    final_event = result["trace_events"][-1]

    assert result["workflow_path"][-1] == "high_risk_review_node"
    assert final_event["node"] == "high_risk_review_node"
    assert final_event["event_type"] == "human_review_required"
    assert final_event["metadata"]["risk_level"] == "high"
    assert final_event["metadata"]["needs_human_review"] is True


def test_empty_ticket_records_validation_failure_and_workflow_error():
    result = run_graph("   ")

    assert result["workflow_path"] == ["validate_input", "error_node"]
    assert event_types(result) == [
        "validation_failed",
        "workflow_error",
    ]
    assert result["trace_events"][0]["node"] == "validate_input"
    assert result["trace_events"][-1]["node"] == "error_node"
    assert result["errors"] == ["Empty user message"]


def test_classification_trace_metadata_includes_classifier_mode():
    result = run_graph("How do I change my profile picture?")

    classification_event = result["trace_events"][1]

    assert classification_event["node"] == "classify_ticket"
    assert classification_event["event_type"] == "mock_classification_completed"
    assert classification_event["metadata"]["classifier_mode"] == "mock"
    assert classification_event["metadata"]["category"] == "general"
    assert classification_event["metadata"]["risk_level"] == "low"