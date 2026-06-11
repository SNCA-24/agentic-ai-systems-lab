from __future__ import annotations

from typing import Any

from app.schemas import RefundEligibilityDecision


HIGH_VALUE_REFUND_THRESHOLD = 100.0


def requires_human_review(refund_amount: float | None, policy_unclear: bool) -> bool:
    if policy_unclear:
        return True

    if refund_amount is not None and refund_amount >= HIGH_VALUE_REFUND_THRESHOLD:
        return True

    return False


def _build_evidence_summary(
    customer_context: dict[str, Any],
    charges: list[dict[str, Any]],
) -> str:
    account_type = customer_context.get("account_type", "unknown")
    status = customer_context.get("subscription_status", "unknown")
    return (
        f"customer_found={customer_context.get('customer_found', False)}; "
        f"account_type={account_type}; "
        f"subscription_status={status}; "
        f"recent_charge_count={len(charges)}; "
        f"refund_history_count={len(customer_context.get('refund_history', []))}; "
        f"intent={customer_context.get('intent', 'unknown')}"
    )


def _decision(
    *,
    refund_eligible: bool | None,
    refund_amount: float | None,
    risk_level: str,
    needs_human_review: bool,
    decision_reason: str,
    policy_basis: list[str],
    evidence_summary: str,
    status: str,
) -> RefundEligibilityDecision:
    return RefundEligibilityDecision(
        refund_eligible=refund_eligible,
        refund_amount=refund_amount,
        risk_level=risk_level,
        needs_human_review=needs_human_review,
        decision_reason=decision_reason,
        policy_basis=policy_basis,
        evidence_summary=evidence_summary,
        status=status,
    )


def _malformed_amount_decision(customer_id: str, evidence_summary: str) -> RefundEligibilityDecision:
    return _decision(
        refund_eligible=None,
        refund_amount=None,
        risk_level="high",
        needs_human_review=True,
        decision_reason=f"Malformed charge amount evidence for {customer_id}; escalate for manual investigation.",
        policy_basis=["refund_policy#escalation-rules"],
        evidence_summary=evidence_summary,
        status="escalated",
    )


def _parse_amount(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def decide_refund_eligibility(
    *,
    customer_context: dict[str, Any],
    billing_evidence: dict[str, Any],
    retrieved_policy_docs: list[dict[str, Any]],
    intent: str,
    user_message: str,
) -> RefundEligibilityDecision:
    del retrieved_policy_docs
    del user_message
    customer_context = dict(customer_context)
    customer_context["intent"] = intent
    charges = list(billing_evidence.get("recent_charges", []))
    evidence_summary = _build_evidence_summary(customer_context, charges)

    customer_id = str(customer_context.get("customer_id", billing_evidence.get("customer_id", "unknown")))
    customer_found = bool(customer_context.get("customer_found", False))
    if not customer_found:
        return _decision(
            refund_eligible=None,
            refund_amount=None,
            risk_level="high",
            needs_human_review=True,
            decision_reason=f"Missing customer evidence for {customer_id}; escalate for manual investigation.",
            policy_basis=["refund_policy#escalation-rules"],
            evidence_summary=evidence_summary,
            status="escalated",
        )

    if not charges:
        return _decision(
            refund_eligible=None,
            refund_amount=None,
            risk_level="high",
            needs_human_review=True,
            decision_reason=f"Missing charge evidence for {customer_id}; escalate for manual investigation.",
            policy_basis=["refund_policy#escalation-rules"],
            evidence_summary=evidence_summary,
            status="escalated",
        )

    if any(charge.get("has_conflicting_evidence") for charge in charges):
        return _decision(
            refund_eligible=None,
            refund_amount=None,
            risk_level="high",
            needs_human_review=True,
            decision_reason="Conflicting billing evidence detected; human review is required before any refund decision.",
            policy_basis=["billing_policy#review-and-escalation-boundaries"],
            evidence_summary=evidence_summary,
            status="human_review",
        )

    duplicate_charge = next((charge for charge in charges if charge.get("is_duplicate")), None)
    if duplicate_charge is not None:
        amount = _parse_amount(duplicate_charge.get("amount"))
        if amount is None:
            return _malformed_amount_decision(customer_id, evidence_summary)
        profile_requires_review = customer_context.get("account_type") == "enterprise"
        human_review = requires_human_review(amount, profile_requires_review)
        status = "human_review" if human_review else "eligible"
        reason = "Duplicate charge confirmed by billing fixtures."
        if profile_requires_review:
            reason = "Duplicate charge confirmed, but enterprise accounts require human review."
        elif amount >= HIGH_VALUE_REFUND_THRESHOLD:
            reason = "Duplicate charge confirmed, but the refund amount requires human review."
        return _decision(
            refund_eligible=True,
            refund_amount=amount,
            risk_level="high" if human_review else "medium",
            needs_human_review=human_review,
            decision_reason=reason,
            policy_basis=["billing_policy#duplicate-charge-detection"],
            evidence_summary=evidence_summary,
            status=status,
        )

    post_cancellation_charge = next(
        (charge for charge in charges if charge.get("charge_timing") == "post_cancellation"),
        None,
    )
    if post_cancellation_charge is not None:
        amount = _parse_amount(post_cancellation_charge.get("amount"))
        if amount is None:
            return _malformed_amount_decision(customer_id, evidence_summary)
        profile_requires_review = customer_context.get("account_type") == "enterprise"
        human_review = requires_human_review(amount, profile_requires_review)
        status = "human_review" if human_review else "eligible"
        reason = "Post-cancellation charge confirmed by billing fixtures."
        if profile_requires_review:
            reason = "Post-cancellation charge confirmed, but enterprise accounts require human review."
        elif amount >= HIGH_VALUE_REFUND_THRESHOLD:
            reason = "Post-cancellation charge confirmed, but the refund amount requires human review."
        return _decision(
            refund_eligible=True,
            refund_amount=amount,
            risk_level="high" if human_review else "medium",
            needs_human_review=human_review,
            decision_reason=reason,
            policy_basis=["cancellation_policy#post-cancellation-charges"],
            evidence_summary=evidence_summary,
            status=status,
        )

    outside_window_charge = next(
        (charge for charge in charges if charge.get("within_refund_window") is False),
        None,
    )
    if outside_window_charge is not None:
        return _decision(
            refund_eligible=False,
            refund_amount=None,
            risk_level="low",
            needs_human_review=False,
            decision_reason="The available billing evidence shows the request is outside the refund window.",
            policy_basis=["refund_policy#refund-window"],
            evidence_summary=evidence_summary,
            status="ineligible",
        )

    parsed_amounts: list[float] = []
    for charge in charges:
        amount = _parse_amount(charge.get("amount"))
        if amount is None:
            return _malformed_amount_decision(customer_id, evidence_summary)
        parsed_amounts.append(amount)

    amount = max(parsed_amounts)
    is_enterprise = customer_context.get("account_type") == "enterprise"
    if is_enterprise or amount >= HIGH_VALUE_REFUND_THRESHOLD:
        reasons = []
        if is_enterprise:
            reasons.append("enterprise account")
        if amount >= HIGH_VALUE_REFUND_THRESHOLD:
            reasons.append("high-value refund amount")
        return _decision(
            refund_eligible=True,
            refund_amount=amount,
            risk_level="high",
            needs_human_review=True,
            decision_reason=f"Eligible scenario found, but {' and '.join(reasons)} requires human review.",
            policy_basis=["refund_policy#review-thresholds"],
            evidence_summary=evidence_summary,
            status="human_review",
        )

    return _decision(
        refund_eligible=None,
        refund_amount=None,
        risk_level="high",
        needs_human_review=True,
        decision_reason="Available evidence does not support an automatic refund decision; escalate for manual review.",
        policy_basis=["refund_policy#escalation-rules"],
        evidence_summary=evidence_summary,
        status="escalated",
    )


def make_refund_decision(
    *,
    customer_id: str,
    customer_profile: dict[str, Any],
    subscription_status: dict[str, Any],
    recent_charges: dict[str, Any],
    cancellation_info: dict[str, Any],
    refund_history: dict[str, Any],
) -> RefundEligibilityDecision:
    customer_context = {
        **customer_profile,
        **subscription_status,
        **cancellation_info,
        **refund_history,
        "customer_id": customer_id,
        "customer_found": (
            customer_profile.get("customer_found", False)
            and subscription_status.get("customer_found", False)
            and cancellation_info.get("customer_found", False)
            and refund_history.get("customer_found", False)
        ),
    }
    return decide_refund_eligibility(
        customer_context=customer_context,
        billing_evidence=recent_charges,
        retrieved_policy_docs=[],
        intent="refund_request",
        user_message="",
    )
