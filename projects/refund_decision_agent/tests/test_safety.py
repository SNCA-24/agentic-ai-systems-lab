from __future__ import annotations

import json
from pathlib import Path
import sys
import types

import pytest

sys.modules.setdefault("dotenv", types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None))

from app import nodes


def _base_state(**overrides):
    state = {
        "request_id": "REQ-001",
        "customer_id": "cust_001",
        "user_message": "I was charged twice and want a refund.",
        "intent": None,
        "category": None,
        "risk_level": None,
        "retrieved_policy_docs": [],
        "billing_evidence": {},
        "customer_context": {},
        "refund_eligible": None,
        "refund_amount": None,
        "needs_human_review": False,
        "decision_reason": None,
        "policy_basis": [],
        "evidence_summary": None,
        "status": None,
        "final_node": None,
        "workflow_path": [],
        "trace_events": [],
        "errors": [],
        "final_response": None,
        "debug": False,
        "classifier_mode": "mock",
        "persistence_status": None,
        "persistence_record": None,
    }
    state.update(overrides)
    return state


@pytest.mark.parametrize(
    ("message", "expected_intent"),
    [
        ("I was charged twice and want a refund.", "duplicate_charge_refund"),
        ("I was billed after cancellation.", "post_cancellation_charge_refund"),
        ("Can you explain the refund window for this charge?", "refund_window_question"),
        ("I need a refund for my enterprise annual account.", "enterprise_refund_request"),
        ("I want a refund.", "general_refund_request"),
        ("The evidence is unclear and conflicting.", "unclear_refund_request"),
    ],
)
def test_mock_classification_uses_canonical_intent_labels(message, expected_intent):
    result = nodes.classify_refund_request_node(_base_state(user_message=message))

    assert result["intent"] == expected_intent


def test_retrieve_policy_context_uses_policy_store_search(monkeypatch):
    captured = {}

    class FakePolicyStore:
        def search(self, *, query, intent=None, limit=3):
            captured["query"] = query
            captured["intent"] = intent
            captured["limit"] = limit
            return []

    monkeypatch.setattr(nodes, "PolicyStore", FakePolicyStore)

    result = nodes.retrieve_policy_context_node(
        _base_state(
            user_message="I was charged twice and want a refund.",
            intent="duplicate_charge_refund",
        )
    )

    assert captured == {
        "query": "I was charged twice and want a refund.",
        "intent": "duplicate_charge_refund",
        "limit": 3,
    }
    assert result["retrieved_policy_docs"] == []


def test_module_exposes_no_real_refund_execution_function():
    exported_names = set(dir(nodes))

    assert "issue_refund" not in exported_names
    assert "process_refund" not in exported_names
    assert "execute_refund" not in exported_names


@pytest.mark.parametrize(
    ("node_fn", "state_overrides"),
    [
        (
            nodes.eligible_response_node,
            {
                "refund_eligible": True,
                "refund_amount": 49.0,
                "decision_reason": "Duplicate charge confirmed by billing fixtures.",
                "policy_basis": ["billing_policy#duplicate-charge-detection"],
                "evidence_summary": "duplicate charge evidence",
                "status": "eligible",
                "risk_level": "medium",
            },
        ),
        (
            nodes.ineligible_response_node,
            {
                "refund_eligible": False,
                "decision_reason": "Outside the refund window.",
                "policy_basis": ["refund_policy#refund-window"],
                "evidence_summary": "outside-window evidence",
                "status": "ineligible",
                "risk_level": "low",
            },
        ),
        (
            nodes.human_review_required_node,
            {
                "refund_eligible": True,
                "refund_amount": 200.0,
                "decision_reason": "Enterprise account requires human review.",
                "policy_basis": ["refund_policy#review-thresholds"],
                "evidence_summary": "enterprise evidence",
                "status": "human_review",
                "risk_level": "high",
                "needs_human_review": True,
            },
        ),
        (
            nodes.escalation_response_node,
            {
                "decision_reason": "Missing charge evidence; escalate for manual investigation.",
                "policy_basis": ["refund_policy#escalation-rules"],
                "evidence_summary": "missing evidence",
                "status": "escalated",
                "risk_level": "high",
                "needs_human_review": True,
            },
        ),
    ],
)
def test_final_response_wording_never_claims_refund_was_executed(node_fn, state_overrides):
    result = node_fn(_base_state(**state_overrides))
    response = result["final_response"].lower()

    forbidden_phrases = (
        "refund was issued",
        "refund has been issued",
        "refund issued",
        "refund was processed",
        "refund has been processed",
        "refund processed",
        "refund was executed",
        "refund has been executed",
        "refund executed",
    )
    assert not any(phrase in response for phrase in forbidden_phrases)


def test_persist_decision_successfully_appends_json_record(tmp_path, monkeypatch):
    records_path = tmp_path / "decision_records.json"
    records_path.write_text("[]\n", encoding="utf-8")
    monkeypatch.setattr(nodes, "DECISION_RECORDS_PATH", records_path)

    result = nodes.persist_decision_node(
        _base_state(
            status="eligible",
            final_node="eligible_response_node",
            refund_eligible=True,
            refund_amount=49.0,
            risk_level="medium",
            decision_reason="Duplicate charge confirmed by billing fixtures.",
            policy_basis=["billing_policy#duplicate-charge-detection"],
            evidence_summary="duplicate charge evidence",
        )
    )

    persisted = json.loads(records_path.read_text(encoding="utf-8"))
    lock_path = Path(f"{records_path}.lock")

    assert result["persistence_status"] == "persisted"
    assert result["persistence_record"]["request_id"] == "REQ-001"
    assert len(persisted) == 1
    assert persisted[0]["request_id"] == "REQ-001"
    assert persisted[0]["final_node"] == "eligible_response_node"
    assert not lock_path.exists()


def test_persist_decision_lock_contention_is_captured_in_state(tmp_path, monkeypatch):
    records_path = tmp_path / "decision_records.json"
    records_path.write_text("[]\n", encoding="utf-8")
    lock_path = Path(f"{records_path}.lock")
    lock_path.write_text("busy\n", encoding="utf-8")
    monkeypatch.setattr(nodes, "DECISION_RECORDS_PATH", records_path)

    result = nodes.persist_decision_node(
        _base_state(
            status="eligible",
            final_node="eligible_response_node",
            refund_eligible=True,
            refund_amount=49.0,
            risk_level="medium",
            decision_reason="Duplicate charge confirmed by billing fixtures.",
            policy_basis=["billing_policy#duplicate-charge-detection"],
            evidence_summary="duplicate charge evidence",
        )
    )

    persisted = json.loads(records_path.read_text(encoding="utf-8"))

    assert result["persistence_status"] == "failed"
    assert result["errors"]
    assert "lock" in result["errors"][-1].lower()
    assert persisted == []


def test_persist_decision_recovers_from_stale_lock(tmp_path, monkeypatch):
    records_path = tmp_path / "decision_records.json"
    records_path.write_text("[]\n", encoding="utf-8")
    lock_path = Path(f"{records_path}.lock")
    lock_path.write_text("stale\n", encoding="utf-8")
    lock_path.touch()
    monkeypatch.setattr(nodes, "DECISION_RECORDS_PATH", records_path)

    original_time = nodes.time.time
    stale_future = original_time() + getattr(nodes, "PERSISTENCE_LOCK_STALE_SECONDS", 5) + 10
    monkeypatch.setattr(nodes.time, "time", lambda: stale_future)

    result = nodes.persist_decision_node(
        _base_state(
            status="eligible",
            final_node="eligible_response_node",
            refund_eligible=True,
            refund_amount=49.0,
            risk_level="medium",
            decision_reason="Duplicate charge confirmed by billing fixtures.",
            policy_basis=["billing_policy#duplicate-charge-detection"],
            evidence_summary="duplicate charge evidence",
        )
    )

    persisted = json.loads(records_path.read_text(encoding="utf-8"))

    assert result["persistence_status"] == "persisted"
    assert len(persisted) == 1
    assert persisted[0]["request_id"] == "REQ-001"
    assert not lock_path.exists()


def test_persist_decision_atomic_write_failure_is_captured_in_state(monkeypatch):
    def fail_open(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "open", fail_open)

    result = nodes.persist_decision_node(
        _base_state(
            status="eligible",
            final_node="eligible_response_node",
            refund_eligible=True,
            refund_amount=49.0,
            risk_level="medium",
            decision_reason="Duplicate charge confirmed by billing fixtures.",
            policy_basis=["billing_policy#duplicate-charge-detection"],
            evidence_summary="duplicate charge evidence",
        )
    )

    assert result["persistence_status"] == "failed"
    assert result["errors"]
    assert "disk full" in result["errors"][-1].lower()
    assert result["status"] == "eligible"


def test_conflicting_evidence_path_does_not_auto_approve():
    decision_state = nodes.decide_refund_eligibility_node(
        _base_state(
            customer_id="cust_005",
            intent="general_refund_request",
            category="billing_issue",
            retrieved_policy_docs=[
                {"section_ref": "billing_policy#review-and-escalation-boundaries"}
            ],
            customer_context={
                "customer_id": "cust_005",
                "customer_found": True,
                "account_type": "standard",
                "plan_name": "Pro Monthly",
                "signup_date": "2025-11-01T00:00:00Z",
                "subscription_status": "active",
                "cancellation_timestamp": None,
                "refund_history": [],
            },
            billing_evidence={
                "customer_id": "cust_005",
                "customer_found": True,
                "subscription_status": "active",
                "cancellation_timestamp": None,
                "recent_charges": [
                    {
                        "charge_id": "ch_conflict_001",
                        "amount": 19.0,
                        "is_duplicate": False,
                        "charge_timing": "standard",
                        "within_refund_window": True,
                        "has_conflicting_evidence": True,
                    }
                ],
                "refund_history": [],
                "conflict_flags": ["conflicting_charge_timing"],
            },
        )
    )

    assert decision_state["refund_eligible"] is None
    assert decision_state["needs_human_review"] is True
    assert decision_state["status"] == "human_review"


def test_missing_evidence_path_does_not_auto_approve():
    decision_state = nodes.decide_refund_eligibility_node(
        _base_state(
            customer_id="cust_missing",
            intent="general_refund_request",
            category="billing_issue",
            retrieved_policy_docs=[
                {"section_ref": "refund_policy#escalation-rules"}
            ],
            customer_context={
                "customer_id": "cust_missing",
                "customer_found": False,
                "account_type": "unknown",
                "plan_name": None,
                "signup_date": None,
                "subscription_status": "unknown",
                "cancellation_timestamp": None,
                "refund_history": [],
            },
            billing_evidence={
                "customer_id": "cust_missing",
                "customer_found": False,
                "subscription_status": "unknown",
                "cancellation_timestamp": None,
                "recent_charges": [],
                "refund_history": [],
                "conflict_flags": [],
            },
        )
    )

    assert decision_state["refund_eligible"] is None
    assert decision_state["needs_human_review"] is True
    assert decision_state["status"] == "escalated"
