from copy import deepcopy

from app.decision_engine import (
    HIGH_VALUE_REFUND_THRESHOLD,
    decide_refund_eligibility,
    make_refund_decision,
)
from app.tools import (
    lookup_cancellation_timestamp,
    lookup_customer_profile,
    lookup_recent_charges,
    lookup_refund_history,
    lookup_subscription_status,
)


def _decision_for(customer_id: str):
    customer_profile = lookup_customer_profile(customer_id)
    subscription_status = lookup_subscription_status(customer_id)
    cancellation_info = lookup_cancellation_timestamp(customer_id)
    refund_history = lookup_refund_history(customer_id)
    recent_charges = lookup_recent_charges(customer_id)

    return decide_refund_eligibility(
        customer_context={
            **customer_profile,
            **subscription_status,
            **cancellation_info,
            **refund_history,
        },
        billing_evidence=recent_charges,
        retrieved_policy_docs=[
            {"section_ref": "billing_policy#duplicate-charge-detection"},
            {"section_ref": "cancellation_policy#post-cancellation-charges"},
            {"section_ref": "refund_policy#refund-window"},
            {"section_ref": "refund_policy#review-thresholds"},
            {"section_ref": "billing_policy#review-and-escalation-boundaries"},
            {"section_ref": "refund_policy#escalation-rules"},
        ],
        intent="refund_request",
        user_message=f"Customer {customer_id} requested a refund.",
    )


def test_duplicate_charge_fixture_is_eligible_without_human_review():
    decision = _decision_for("cust_001")

    assert decision.status == "eligible"
    assert decision.refund_eligible is True
    assert decision.refund_amount == 49.0
    assert decision.needs_human_review is False
    assert decision.risk_level == "medium"
    assert "duplicate" in decision.decision_reason.lower()
    assert decision.policy_basis == ["billing_policy#duplicate-charge-detection"]


def test_post_cancellation_charge_fixture_is_eligible():
    decision = _decision_for("cust_002")

    assert decision.status == "eligible"
    assert decision.refund_eligible is True
    assert decision.refund_amount == 29.0
    assert decision.needs_human_review is False
    assert decision.risk_level == "medium"
    assert "post-cancellation" in decision.decision_reason.lower()
    assert decision.policy_basis == ["cancellation_policy#post-cancellation-charges"]


def test_outside_window_decision_is_ineligible():
    decision = _decision_for("cust_003")

    assert decision.status == "ineligible"
    assert decision.refund_eligible is False
    assert decision.refund_amount is None
    assert decision.needs_human_review is False
    assert decision.policy_basis == ["refund_policy#refund-window"]
    assert "outside" in decision.decision_reason.lower()


def test_enterprise_high_value_decision_requires_human_review():
    decision = _decision_for("cust_004")

    assert HIGH_VALUE_REFUND_THRESHOLD == 100.0
    assert decision.status == "human_review"
    assert decision.refund_eligible is True
    assert decision.refund_amount == 200.0
    assert decision.needs_human_review is True
    assert decision.risk_level == "high"
    assert "enterprise" in decision.decision_reason.lower()
    assert decision.policy_basis == ["refund_policy#review-thresholds"]


def test_conflicting_evidence_does_not_auto_approve():
    decision = _decision_for("cust_005")

    assert decision.status == "human_review"
    assert decision.refund_eligible is None
    assert decision.needs_human_review is True
    assert decision.risk_level == "high"
    assert "conflicting" in decision.decision_reason.lower()
    assert decision.policy_basis == ["billing_policy#review-and-escalation-boundaries"]


def test_missing_customer_or_evidence_escalates():
    decision = _decision_for("cust_missing")

    assert decision.status == "escalated"
    assert decision.refund_eligible is None
    assert decision.refund_amount is None
    assert decision.needs_human_review is True
    assert decision.risk_level == "high"
    assert "missing" in decision.decision_reason.lower()
    assert decision.policy_basis == ["refund_policy#escalation-rules"]


def test_exact_threshold_amount_requires_human_review():
    decision = decide_refund_eligibility(
        customer_context={
            "customer_id": "cust_threshold",
            "customer_found": True,
            "account_type": "standard",
            "subscription_status": "active",
            "refund_history": [],
        },
        billing_evidence={
            "customer_id": "cust_threshold",
            "customer_found": True,
            "recent_charges": [
                {
                    "charge_id": "ch_threshold_001",
                    "amount": 100.0,
                    "is_duplicate": True,
                    "charge_timing": "standard",
                    "within_refund_window": True,
                    "has_conflicting_evidence": False,
                }
            ],
        },
        retrieved_policy_docs=[],
        intent="refund_request",
        user_message="Refund my duplicate charge.",
    )

    assert decision.status == "human_review"
    assert decision.refund_eligible is True
    assert decision.refund_amount == 100.0
    assert decision.needs_human_review is True
    assert decision.risk_level == "high"
    assert "human review" in decision.decision_reason.lower()


def test_malformed_charge_amount_escalates_instead_of_crashing():
    decision = decide_refund_eligibility(
        customer_context={
            "customer_id": "cust_bad_amount",
            "customer_found": True,
            "account_type": "standard",
            "subscription_status": "active",
            "refund_history": [],
        },
        billing_evidence={
            "customer_id": "cust_bad_amount",
            "customer_found": True,
            "recent_charges": [
                {
                    "charge_id": "ch_bad_amount_001",
                    "amount": "not-a-number",
                    "is_duplicate": True,
                    "charge_timing": "standard",
                    "within_refund_window": True,
                    "has_conflicting_evidence": False,
                }
            ],
        },
        retrieved_policy_docs=[],
        intent="refund_request",
        user_message="Refund my duplicate charge.",
    )

    assert decision.status == "escalated"
    assert decision.refund_eligible is None
    assert decision.refund_amount is None
    assert decision.needs_human_review is True
    assert decision.risk_level == "high"
    assert "malformed" in decision.decision_reason.lower()
    assert decision.policy_basis == ["refund_policy#escalation-rules"]


def test_make_refund_decision_wrapper_returns_fixture_decision():
    decision = make_refund_decision(
        customer_id="cust_001",
        customer_profile=lookup_customer_profile("cust_001"),
        subscription_status=lookup_subscription_status("cust_001"),
        recent_charges=lookup_recent_charges("cust_001"),
        cancellation_info=lookup_cancellation_timestamp("cust_001"),
        refund_history=lookup_refund_history("cust_001"),
    )

    assert decision.status == "eligible"
    assert decision.refund_eligible is True
    assert decision.refund_amount == 49.0
    assert decision.risk_level == "medium"


def test_make_refund_decision_wrapper_keeps_customer_found_true_when_charges_are_missing():
    recent_charges = deepcopy(lookup_recent_charges("cust_001"))
    recent_charges["recent_charges"] = []

    decision = make_refund_decision(
        customer_id="cust_001",
        customer_profile=lookup_customer_profile("cust_001"),
        subscription_status=lookup_subscription_status("cust_001"),
        recent_charges=recent_charges,
        cancellation_info=lookup_cancellation_timestamp("cust_001"),
        refund_history=lookup_refund_history("cust_001"),
    )

    assert decision.status == "escalated"
    assert decision.refund_eligible is None
    assert decision.needs_human_review is True
    assert "missing charge evidence" in decision.decision_reason.lower()
