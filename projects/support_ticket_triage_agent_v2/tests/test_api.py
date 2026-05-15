from fastapi.testclient import TestClient

from app.action_store import clear_action_store
from app.api import app
from app.approval_store import clear_approval_store

client = TestClient(app)


def setup_function():
    clear_approval_store()
    clear_action_store()


def test_health_check_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["classifier_mode"] == "mock"
    assert body["environment"] in {"local", "ci"}


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
    assert body["approval_status"] == "not_required"
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
    assert body["approval_status"] == "pending"
    assert body["workflow_path"] == [
        "validate_input",
        "classify_ticket",
        "high_risk_review_node",
    ]
    assert body["trace_events_count"] == 3
    assert body["final_response"].startswith("This request appears high-risk")
    assert "pending human approval" in body["final_response"]


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
    assert body["approval_status"] == "not_required"
    assert body["workflow_path"] == [
        "validate_input",
        "error_node",
    ]
    assert body["trace_events_count"] == 2
    assert body["errors"] == ["Empty user message"]


def test_approval_endpoint_records_approved_decision():
    response = client.post(
        "/tickets/API-004/approval",
        json={
            "approved": True,
            "approval_id": "approval_123",
            "approved_by": "manager_001",
            "approval_notes": "Requester verified and action approved.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == "API-004"
    assert body["approval_status"] == "approved"
    assert body["approval_id"] == "approval_123"
    assert body["approved_by"] == "manager_001"
    assert body["approval_notes"] == "Requester verified and action approved."
    assert body["message"] == "Approval recorded. Workflow can now be resumed safely."


def test_approval_endpoint_rejects_missing_approval_id_for_approved_decision():
    response = client.post(
        "/tickets/API-005/approval",
        json={
            "approved": True,
            "approved_by": "manager_001",
            "approval_notes": "Missing approval ID.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == "API-005"
    assert body["approval_status"] == "rejected"
    assert body["approval_id"] is None
    assert body["approved_by"] == "manager_001"
    assert body["approval_notes"] == "Missing approval ID."
    assert body["message"] == "Approval was not accepted because approval_id is required when approved is true."


def test_approval_endpoint_records_rejected_decision():
    response = client.post(
        "/tickets/API-006/approval",
        json={
            "approved": False,
            "approved_by": "manager_001",
            "approval_notes": "Requester verification failed.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == "API-006"
    assert body["approval_status"] == "rejected"
    assert body["approval_id"] is None
    assert body["approved_by"] == "manager_001"
    assert body["approval_notes"] == "Requester verification failed."
    assert body["message"] == "Approval rejected. No write action has been executed."


def test_approval_decision_can_be_retrieved_after_recording():
    post_response = client.post(
        "/tickets/API-007/approval",
        json={
            "approved": True,
            "approval_id": "approval_777",
            "approved_by": "manager_002",
            "approval_notes": "Approved after verification.",
        },
    )
    assert post_response.status_code == 200

    get_response = client.get("/tickets/API-007/approval")

    assert get_response.status_code == 200
    body = get_response.json()
    assert body["ticket_id"] == "API-007"
    assert body["approval_status"] == "approved"
    assert body["approval_id"] == "approval_777"
    assert body["approved_by"] == "manager_002"
    assert body["approval_notes"] == "Approved after verification."


def test_get_approval_returns_404_when_missing():
    response = client.get("/tickets/UNKNOWN/approval")

    assert response.status_code == 404
    assert response.json()["detail"] == "No approval decision found for ticket_id=UNKNOWN."


def test_resume_endpoint_routes_approved_decision():
    approval_response = client.post(
        "/tickets/API-008/approval",
        json={
            "approved": True,
            "approval_id": "approval_888",
            "approved_by": "manager_003",
            "approval_notes": "Approved for resume test.",
        },
    )
    assert approval_response.status_code == 200

    resume_response = client.post("/tickets/API-008/resume")

    assert resume_response.status_code == 200
    body = resume_response.json()
    assert body["ticket_id"] == "API-008"
    assert body["approval_status"] == "approved"
    assert body["approval_id"] == "approval_888"
    assert body["approved_by"] == "manager_003"
    assert body["workflow_path"] == [
        "approval_resume_entry_node",
        "approval_approved_node",
        "execute_approved_action_node",
    ]
    assert body["trace_events_count"] == 2
    assert body["tool_results_count"] == 1
    assert body["errors"] == []
    assert "simulated successfully" in body["final_response"]


def test_resume_endpoint_routes_rejected_decision():
    approval_response = client.post(
        "/tickets/API-009/approval",
        json={
            "approved": False,
            "approved_by": "manager_003",
            "approval_notes": "Rejected for resume test.",
        },
    )
    assert approval_response.status_code == 200

    resume_response = client.post("/tickets/API-009/resume")

    assert resume_response.status_code == 200
    body = resume_response.json()
    assert body["ticket_id"] == "API-009"
    assert body["approval_status"] == "rejected"
    assert body["workflow_path"] == [
        "approval_resume_entry_node",
        "approval_rejected_node",
    ]
    assert body["trace_events_count"] == 1
    assert body["errors"] == []
    assert "remains blocked" in body["final_response"]


def test_resume_endpoint_returns_404_when_approval_missing():
    clear_approval_store()
    response = client.post("/tickets/UNKNOWN/resume")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cannot resume ticket_id=UNKNOWN because no approval decision was found."