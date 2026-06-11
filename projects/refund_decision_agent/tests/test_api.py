import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api import app
from app.schemas import DecisionRecord, RefundDecisionRequest, RefundDecisionResponse, TraceEvent


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch):
    from app import nodes

    records_path = tmp_path / "decision_records.json"
    records_path.write_text("[]\n", encoding="utf-8")
    monkeypatch.setattr(nodes, "DECISION_RECORDS_PATH", records_path)
    return TestClient(app)


@pytest.mark.parametrize(
    "field_name, payload",
    [
        ("request_id", {"request_id": "   ", "customer_id": "cust_001", "user_message": "Need a refund."}),
        ("customer_id", {"request_id": "REQ-001", "customer_id": "", "user_message": "Need a refund."}),
        ("user_message", {"request_id": "REQ-001", "customer_id": "cust_001", "user_message": "   "}),
    ],
)
def test_refund_decision_request_rejects_blank_required_fields(field_name, payload):
    with pytest.raises(ValidationError) as exc_info:
        RefundDecisionRequest(**payload)

    assert field_name in str(exc_info.value)
    assert "must not be blank" in str(exc_info.value)


def test_refund_decision_request_defaults_debug_to_false():
    request = RefundDecisionRequest(
        request_id="REQ-000",
        customer_id="cust_000",
        user_message="Please check my refund eligibility.",
    )

    assert request.debug is False
    assert request.model_dump()["debug"] is False


def test_refund_decision_request_rejects_non_string_input_via_validation():
    with pytest.raises(ValidationError) as exc_info:
        RefundDecisionRequest(
            request_id=123,
            customer_id="cust_001",
            user_message="Need a refund.",
        )

    assert "request_id" in str(exc_info.value)
    assert "must be a string" in str(exc_info.value)


@pytest.mark.parametrize(
    "field_name, payload",
    [
        ("request_id", {"request_id": "   ", "customer_id": "cust_001", "final_node": "eligible", "status": "eligible"}),
        ("customer_id", {"request_id": "REQ-001", "customer_id": "", "final_node": "eligible", "status": "eligible"}),
        ("final_node", {"request_id": "REQ-001", "customer_id": "cust_001", "final_node": "   ", "status": "eligible"}),
    ],
)
def test_decision_record_rejects_blank_identifiers(field_name, payload):
    with pytest.raises(ValidationError) as exc_info:
        DecisionRecord(
            refund_eligible=True,
            refund_amount=29.0,
            risk_level="medium",
            needs_human_review=False,
            decision_reason="Eligible under the mock policy.",
            policy_basis=["refund_window"],
            evidence_summary="Evidence supports a refund.",
            timestamp="2026-06-11T00:00:00Z",
            **payload,
        )

    assert field_name in str(exc_info.value)
    assert "must not be blank" in str(exc_info.value)


def test_refund_decision_response_public_dump_hides_debug_fields_when_debug_disabled():
    response = RefundDecisionResponse(
        request_id="REQ-001",
        customer_id="cust_001",
        status="eligible",
        refund_eligible=True,
        refund_amount=29.0,
        risk_level="medium",
        needs_human_review=False,
        decision_reason="The demo evidence supports the refund.",
        policy_basis=["refund_window", "billing_history"],
        evidence_summary="Customer was charged after cancellation in the mock dataset.",
        final_response="You appear eligible for a refund based on the demo evidence available.",
        workflow_path=["validate_input", "classify_intent", "eligible_response_node"],
        trace_events=[
            TraceEvent(
                node="validate_input",
                event_type="checkpoint",
                message="Input validated.",
                metadata={"phase": "request"},
            )
        ],
        errors=["hidden internal note"],
        debug=False,
    )

    public_body = response.public_dump()

    assert public_body == {
        "request_id": "REQ-001",
        "customer_id": "cust_001",
        "status": "eligible",
        "refund_eligible": True,
        "refund_amount": 29.0,
        "risk_level": "medium",
        "needs_human_review": False,
        "decision_reason": "The demo evidence supports the refund.",
        "policy_basis": ["refund_window", "billing_history"],
        "evidence_summary": "Customer was charged after cancellation in the mock dataset.",
        "final_response": "You appear eligible for a refund based on the demo evidence available.",
    }


def test_refund_decision_response_public_dump_keeps_debug_fields_when_debug_enabled():
    response = RefundDecisionResponse(
        request_id="REQ-002",
        customer_id="cust_002",
        status="ineligible",
        refund_eligible=False,
        refund_amount=None,
        risk_level="low",
        needs_human_review=False,
        decision_reason="The policy window has expired.",
        policy_basis=["refund_window"],
        evidence_summary="The mock purchase falls outside the refund window.",
        final_response="You are not eligible for a refund under the demo policy.",
        workflow_path=["validate_input", "policy_review_node"],
        trace_events=[
            TraceEvent(
                node="policy_review_node",
                event_type="decision",
                message="Policy review completed.",
                metadata={"policy_basis": ["refund_window"]},
            )
        ],
        errors=["no issues"],
        debug=True,
    )

    public_body = response.public_dump()

    assert public_body["workflow_path"] == ["validate_input", "policy_review_node"]
    assert public_body["trace_events"][0]["node"] == "policy_review_node"
    assert public_body["errors"] == ["no issues"]
    assert public_body["debug"] is True
    assert public_body["status"] == "ineligible"


def test_refund_decide_endpoint_duplicate_charge_returns_200_and_hides_debug_fields_by_default(client: TestClient):
    response = client.post(
        "/refunds/decide",
        json={
            "request_id": "REQ-API-001",
            "customer_id": "cust_001",
            "user_message": "I was charged twice for the same invoice and need a refund.",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["request_id"] == "REQ-API-001"
    assert body["customer_id"] == "cust_001"
    assert body["status"] == "eligible"
    assert body["refund_eligible"] is True
    assert "workflow_path" not in body
    assert "trace_events" not in body
    assert "errors" not in body
    assert "debug" not in body


def test_refund_decide_endpoint_debug_mode_exposes_internal_fields(client: TestClient):
    response = client.post(
        "/refunds/decide?debug=true",
        json={
            "request_id": "REQ-API-002",
            "customer_id": "cust_missing",
            "user_message": "I need a refund for a charge on my missing account.",
            "debug": False,
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "escalated"
    assert body["debug"] is True
    assert isinstance(body["workflow_path"], list)
    assert body["workflow_path"]
    assert body["workflow_path"][0] == "validate_input_node"
    assert body["workflow_path"][-1] == "persist_decision_node"
    assert "escalation_response_node" in body["workflow_path"]
    assert isinstance(body["trace_events"], list)
    assert body["trace_events"]
    assert body["errors"] == []


def test_refund_decide_endpoint_bad_payload_returns_422(client: TestClient):
    response = client.post(
        "/refunds/decide",
        json={
            "request_id": "REQ-API-003",
            "customer_id": "",
            "user_message": "Need a refund.",
        },
    )

    assert response.status_code == 422
