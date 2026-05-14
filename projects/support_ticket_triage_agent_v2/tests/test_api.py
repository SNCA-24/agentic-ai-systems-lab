

from fastapi.testclient import TestClient

from app.api import app


client = TestClient(app)


def test_health_check_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["classifier_mode"] == "mock"
    assert body["environment"] == "local"


def test_triage_endpoint_routes_billing_ticket():
    response = client.post(
        "/tickets/triage",
        json={
            "ticket_id": "API-001",
            "user_message": "I was charged twice for my subscription.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == "API-001"
    assert body["category"] == "billing"
    assert body["risk_level"] == "medium"
    assert body["needs_human_review"] is False
    assert body["workflow_path"] == [
        "validate_input",
        "classify_ticket",
        "billing_node",
    ]
    assert body["trace_events_count"] == 3


def test_triage_endpoint_routes_high_risk_ticket():
    response = client.post(
        "/tickets/triage",
        json={
            "ticket_id": "API-002",
            "user_message": "Please give this employee admin access immediately.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "technical"
    assert body["risk_level"] == "high"
    assert body["needs_human_review"] is True
    assert body["workflow_path"] == [
        "validate_input",
        "classify_ticket",
        "high_risk_review_node",
    ]
    assert body["trace_events_count"] == 3
    assert body["final_response"].startswith("This request appears high-risk")


def test_triage_endpoint_handles_empty_ticket():
    response = client.post(
        "/tickets/triage",
        json={
            "ticket_id": "API-003",
            "user_message": "   ",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "unknown"
    assert body["intent"] == "empty_message"
    assert body["workflow_path"] == [
        "validate_input",
        "error_node",
    ]
    assert body["trace_events_count"] == 2
    assert body["errors"] == ["Empty user message"]