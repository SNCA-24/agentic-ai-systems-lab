from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any

from app.config import CLASSIFIER_MODE, DECISION_RECORDS_PATH
from app.decision_engine import decide_refund_eligibility
from app.policy_store import PolicyStore
from app.schemas import (
    BillingLookupResult,
    DecisionRecord,
    RefundDecisionRequest,
    RefundEligibilityDecision,
    RefundIntentClassification,
)
from app.state import RefundDecisionState
from app.tools import (
    lookup_cancellation_timestamp,
    lookup_customer_profile,
    lookup_recent_charges,
    lookup_refund_history,
    lookup_subscription_status,
)
from app.tracing import add_trace_event, append_workflow_path


PERSISTENCE_LOCK_STALE_SECONDS = 5


def _state_copy(state: RefundDecisionState) -> RefundDecisionState:
    copied = dict(state)
    copied.setdefault("workflow_path", [])
    copied.setdefault("trace_events", [])
    copied.setdefault("errors", [])
    copied.setdefault("policy_basis", [])
    copied.setdefault("retrieved_policy_docs", [])
    copied.setdefault("billing_evidence", {})
    copied.setdefault("customer_context", {})
    copied.setdefault("needs_human_review", False)
    copied.setdefault("debug", False)
    copied.setdefault("classifier_mode", CLASSIFIER_MODE)
    copied.setdefault("persistence_status", None)
    copied.setdefault("persistence_record", None)
    return copied


def _enter_node(state: RefundDecisionState, node_name: str) -> RefundDecisionState:
    next_state = _state_copy(state)
    next_state["workflow_path"] = append_workflow_path(next_state["workflow_path"], node_name)
    next_state["trace_events"] = add_trace_event(
        next_state["trace_events"],
        node=node_name,
        event_type="node_started",
        message=f"{node_name} started.",
    )
    return next_state


def _trace(
    state: RefundDecisionState,
    *,
    node_name: str,
    event_type: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> RefundDecisionState:
    state["trace_events"] = add_trace_event(
        state["trace_events"],
        node=node_name,
        event_type=event_type,
        message=message,
        metadata=metadata,
    )
    return state


def _record_error(
    state: RefundDecisionState,
    *,
    node_name: str,
    error: Exception,
    message: str,
    status: str | None = None,
) -> RefundDecisionState:
    next_state = _state_copy(state)
    next_state["errors"] = [*next_state["errors"], f"{node_name}: {message}: {error}"]
    if status is not None:
        next_state["status"] = status
    next_state["needs_human_review"] = True
    return _trace(
        next_state,
        node_name=node_name,
        event_type="node_error",
        message=message,
        metadata={"error_type": error.__class__.__name__, "error": str(error)},
    )


def _mock_classification(message: str) -> RefundIntentClassification:
    lowered = message.lower()
    if any(term in lowered for term in ("unclear", "conflict", "missing evidence", "not sure")):
        return RefundIntentClassification(
            intent="unclear_refund_request",
            category="manual_review",
            confidence=0.9,
            risk_level="high",
        )
    if any(term in lowered for term in ("duplicate", "charged twice", "double charge")):
        return RefundIntentClassification(
            intent="duplicate_charge_refund",
            category="billing_issue",
            confidence=0.97,
            risk_level="medium",
        )
    if any(term in lowered for term in ("refund window", "window for refund", "eligible window")):
        return RefundIntentClassification(
            intent="refund_window_question",
            category="policy_question",
            confidence=0.9,
            risk_level="low",
        )
    if "enterprise" in lowered:
        return RefundIntentClassification(
            intent="enterprise_refund_request",
            category="billing_issue",
            confidence=0.91,
            risk_level="high",
        )
    if any(term in lowered for term in ("after cancellation", "post-cancellation", "post cancellation", "cancelled", "cancellation")):
        return RefundIntentClassification(
            intent="post_cancellation_charge_refund",
            category="billing_issue",
            confidence=0.94,
            risk_level="medium",
        )
    return RefundIntentClassification(
        intent="general_refund_request",
        category="general_refund",
        confidence=0.88,
        risk_level="low",
    )


def _decision_intent(intent: str | None) -> str:
    canonical_intent = (intent or "").strip()
    if canonical_intent in {
        "duplicate_charge_refund",
        "unclear_refund_request",
    }:
        return canonical_intent
    if canonical_intent in {
        "post_cancellation_charge_refund",
    }:
        return "cancellation_dispute"
    if canonical_intent in {
        "general_refund_request",
        "enterprise_refund_request",
        "refund_window_question",
        "",
    }:
        return "refund_request"
    return canonical_intent


def _classification_metadata(classification: RefundIntentClassification, requested_mode: str) -> dict[str, Any]:
    return {
        "intent": classification.intent,
        "category": classification.category,
        "confidence": classification.confidence,
        "risk_level": classification.risk_level,
        "classifier_mode": "mock",
        "requested_classifier_mode": requested_mode,
    }


def _retrieved_documents(query: str, intent: str | None) -> list[dict[str, Any]]:
    return [
        document.model_dump()
        for document in PolicyStore().search(
            query=query,
            intent=intent,
            limit=3,
        )
    ]


def _lock_path(records_path: Path) -> Path:
    return Path(f"{records_path}.lock")


def _temp_path(records_path: Path) -> Path:
    return records_path.with_name(f"{records_path.name}.tmp.{os.getpid()}")


def _lock_is_stale(lock_path: Path) -> bool:
    age_seconds = time.time() - lock_path.stat().st_mtime
    return age_seconds > PERSISTENCE_LOCK_STALE_SECONDS


def _clear_stale_lock(lock_path: Path) -> None:
    if _lock_is_stale(lock_path):
        lock_path.unlink()


def _acquire_persistence_lock(records_path: Path) -> Path:
    lock_path = _lock_path(records_path)
    try:
        file_descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        try:
            _clear_stale_lock(lock_path)
        except Exception as cleanup_error:
            raise OSError(f"Failed to clear stale persistence lock: {lock_path}") from cleanup_error
        try:
            file_descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as lock_error:
            raise FileExistsError(f"Persistence lock already exists: {lock_path}") from lock_error

    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(f"{os.getpid()}\n")
    except Exception:
        try:
            lock_path.unlink(missing_ok=True)
        finally:
            raise
    return lock_path


def _release_persistence_lock(lock_path: Path) -> None:
    lock_path.unlink(missing_ok=True)


def _load_persisted_records(records_path: Path) -> list[dict[str, Any]]:
    if not records_path.exists():
        return []
    with records_path.open(encoding="utf-8") as handle:
        existing_records = json.load(handle)
    if not isinstance(existing_records, list):
        raise ValueError("decision_records.json must contain a JSON array")
    return existing_records


def _atomic_write_records(records_path: Path, records: list[dict[str, Any]]) -> None:
    temp_path = _temp_path(records_path)
    try:
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(records, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, records_path)
    finally:
        temp_path.unlink(missing_ok=True)


def _policy_refs(documents: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for doc in documents:
        section_ref = doc.get("section_ref")
        if isinstance(section_ref, str) and section_ref.strip():
            refs.append(section_ref)
    return refs


def _conflict_flags(recent_charges: list[dict[str, Any]]) -> list[str]:
    flags: list[str] = []
    if any(charge.get("has_conflicting_evidence") for charge in recent_charges):
        flags.append("conflicting_billing_evidence")
    if not recent_charges:
        flags.append("missing_recent_charges")
    return flags


def validate_input_node(state: RefundDecisionState) -> RefundDecisionState:
    node_name = "validate_input_node"
    next_state = _enter_node(state, node_name)
    try:
        request = RefundDecisionRequest(
            request_id=next_state.get("request_id"),
            customer_id=next_state.get("customer_id"),
            user_message=next_state.get("user_message"),
            debug=bool(next_state.get("debug", False)),
        )
        next_state.update(request.model_dump())
        next_state["classifier_mode"] = next_state.get("classifier_mode") or CLASSIFIER_MODE
        return _trace(
            next_state,
            node_name=node_name,
            event_type="input_validated",
            message="Validated refund request input.",
            metadata={"debug": request.debug, "classifier_mode": next_state["classifier_mode"]},
        )
    except Exception as error:
        next_state["status"] = "escalated"
        next_state["decision_reason"] = "The refund request input could not be validated safely."
        return _record_error(
            next_state,
            node_name=node_name,
            error=error,
            message="Input validation failed",
            status="escalated",
        )


def classify_refund_request_node(state: RefundDecisionState) -> RefundDecisionState:
    node_name = "classify_refund_request_node"
    next_state = _enter_node(state, node_name)
    try:
        classifier_mode = str(next_state.get("classifier_mode") or CLASSIFIER_MODE).lower()
        classification = _mock_classification(str(next_state.get("user_message", "")))
        next_state["classifier_mode"] = classifier_mode or "mock"
        if classifier_mode != "mock":
            next_state = _trace(
                next_state,
                node_name=node_name,
                event_type="classifier_mode_fallback",
                message="Non-mock classifier mode requested; using deterministic mock classifier.",
                metadata={"requested_mode": classifier_mode, "effective_mode": "mock"},
            )
        next_state["classifier_mode"] = "mock"
        next_state["intent"] = classification.intent
        next_state["category"] = classification.category
        next_state["risk_level"] = classification.risk_level
        return _trace(
            next_state,
            node_name=node_name,
            event_type="classification_completed",
            message="Classified refund request using deterministic mock logic.",
            metadata=_classification_metadata(classification, classifier_mode),
        )
    except Exception as error:
        next_state["intent"] = "unclear_refund_request"
        next_state["category"] = "manual_review"
        next_state["risk_level"] = "high"
        next_state["status"] = "escalated"
        next_state["decision_reason"] = "The request could not be classified safely and needs manual review."
        return _record_error(
            next_state,
            node_name=node_name,
            error=error,
            message="Refund classification failed",
            status="escalated",
        )


def retrieve_policy_context_node(state: RefundDecisionState) -> RefundDecisionState:
    node_name = "retrieve_policy_context_node"
    next_state = _enter_node(state, node_name)
    try:
        documents = _retrieved_documents(
            query=str(next_state.get("user_message", "")),
            intent=next_state.get("intent"),
        )
        next_state["retrieved_policy_docs"] = documents
        return _trace(
            next_state,
            node_name=node_name,
            event_type="policy_retrieval_completed",
            message="Retrieved refund policy context.",
            metadata={
                "doc_count": len(documents),
                "sources": sorted({document["source"] for document in documents}),
            },
        )
    except Exception as error:
        next_state["retrieved_policy_docs"] = []
        next_state["status"] = "escalated"
        next_state["decision_reason"] = "Policy retrieval failed, so the request requires manual review."
        return _record_error(
            next_state,
            node_name=node_name,
            error=error,
            message="Policy retrieval failed",
            status="escalated",
        )


def lookup_billing_evidence_node(state: RefundDecisionState) -> RefundDecisionState:
    node_name = "lookup_billing_evidence_node"
    next_state = _enter_node(state, node_name)
    try:
        customer_id = str(next_state.get("customer_id", ""))
        customer_profile = lookup_customer_profile(customer_id)
        subscription_status = lookup_subscription_status(customer_id)
        cancellation_info = lookup_cancellation_timestamp(customer_id)
        refund_history = lookup_refund_history(customer_id)
        recent_charges = lookup_recent_charges(customer_id)

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
        evidence = BillingLookupResult(
            customer_found=bool(customer_context["customer_found"]),
            subscription_status=subscription_status.get("subscription_status"),
            cancellation_timestamp=cancellation_info.get("cancellation_timestamp"),
            recent_charges=recent_charges.get("recent_charges", []),
            refund_history=refund_history.get("refund_history", []),
            conflict_flags=_conflict_flags(recent_charges.get("recent_charges", [])),
        ).model_dump()
        evidence["customer_id"] = customer_id
        next_state["customer_context"] = customer_context
        next_state["billing_evidence"] = evidence
        return _trace(
            next_state,
            node_name=node_name,
            event_type="billing_evidence_loaded",
            message="Loaded mock billing and customer evidence.",
            metadata={
                "customer_found": evidence["customer_found"],
                "recent_charge_count": len(evidence["recent_charges"]),
                "conflict_flags": evidence["conflict_flags"],
            },
        )
    except Exception as error:
        next_state["customer_context"] = {
            "customer_id": next_state.get("customer_id"),
            "customer_found": False,
        }
        next_state["billing_evidence"] = {
            "customer_id": next_state.get("customer_id"),
            "customer_found": False,
            "recent_charges": [],
            "refund_history": [],
            "conflict_flags": ["billing_lookup_failed"],
        }
        next_state["status"] = "escalated"
        next_state["decision_reason"] = "Billing evidence lookup failed, so the request requires manual review."
        return _record_error(
            next_state,
            node_name=node_name,
            error=error,
            message="Billing evidence lookup failed",
            status="escalated",
        )


def decide_refund_eligibility_node(state: RefundDecisionState) -> RefundDecisionState:
    node_name = "decide_refund_eligibility_node"
    next_state = _enter_node(state, node_name)
    try:
        decision = decide_refund_eligibility(
            customer_context=next_state.get("customer_context", {}),
            billing_evidence=next_state.get("billing_evidence", {}),
            retrieved_policy_docs=next_state.get("retrieved_policy_docs", []),
            intent=_decision_intent(next_state.get("intent")),
            user_message=str(next_state.get("user_message") or ""),
        )
        assert isinstance(decision, RefundEligibilityDecision)
        next_state["refund_eligible"] = decision.refund_eligible
        next_state["refund_amount"] = decision.refund_amount
        next_state["risk_level"] = decision.risk_level
        next_state["needs_human_review"] = decision.needs_human_review
        next_state["decision_reason"] = decision.decision_reason
        next_state["policy_basis"] = decision.policy_basis
        next_state["evidence_summary"] = decision.evidence_summary
        next_state["status"] = decision.status
        return _trace(
            next_state,
            node_name=node_name,
            event_type="decision_completed",
            message="Completed structured refund eligibility decision.",
            metadata={
                "status": decision.status,
                "refund_eligible": decision.refund_eligible,
                "needs_human_review": decision.needs_human_review,
                "policy_basis": decision.policy_basis,
            },
        )
    except Exception as error:
        next_state["refund_eligible"] = None
        next_state["refund_amount"] = None
        next_state["risk_level"] = "high"
        next_state["needs_human_review"] = True
        next_state["decision_reason"] = "Refund eligibility could not be determined safely and needs manual review."
        next_state["policy_basis"] = _policy_refs(next_state.get("retrieved_policy_docs", []))
        next_state["evidence_summary"] = None
        next_state["status"] = "escalated"
        return _record_error(
            next_state,
            node_name=node_name,
            error=error,
            message="Refund decisioning failed",
            status="escalated",
        )


def eligible_response_node(state: RefundDecisionState) -> RefundDecisionState:
    node_name = "eligible_response_node"
    next_state = _enter_node(state, node_name)
    try:
        amount = next_state.get("refund_amount")
        amount_text = f"${amount:.2f}" if isinstance(amount, (int, float)) else "the relevant amount"
        next_state["status"] = "eligible"
        next_state["final_node"] = node_name
        next_state["final_response"] = (
            f"You appear eligible for a refund review of {amount_text}. "
            "This demo can explain the policy and billing evidence supporting the decision, "
            "but it does not issue or process refunds."
        )
        return _trace(
            next_state,
            node_name=node_name,
            event_type="response_prepared",
            message="Prepared eligible response.",
            metadata={"refund_amount": amount, "policy_basis": next_state.get("policy_basis", [])},
        )
    except Exception as error:
        next_state["status"] = "escalated"
        next_state["final_node"] = node_name
        next_state["final_response"] = (
            "The request appears to need manual review before any refund decision can be finalized."
        )
        return _record_error(
            next_state,
            node_name=node_name,
            error=error,
            message="Eligible response generation failed",
            status="escalated",
        )


def ineligible_response_node(state: RefundDecisionState) -> RefundDecisionState:
    node_name = "ineligible_response_node"
    next_state = _enter_node(state, node_name)
    try:
        next_state["status"] = "ineligible"
        next_state["final_node"] = node_name
        next_state["final_response"] = (
            "Based on the available policy and billing evidence in this demo, "
            "the request does not appear eligible for a refund."
        )
        return _trace(
            next_state,
            node_name=node_name,
            event_type="response_prepared",
            message="Prepared ineligible response.",
            metadata={"policy_basis": next_state.get("policy_basis", [])},
        )
    except Exception as error:
        next_state["status"] = "escalated"
        next_state["final_node"] = node_name
        next_state["final_response"] = (
            "The request could not be resolved automatically and needs manual review."
        )
        return _record_error(
            next_state,
            node_name=node_name,
            error=error,
            message="Ineligible response generation failed",
            status="escalated",
        )


def human_review_required_node(state: RefundDecisionState) -> RefundDecisionState:
    node_name = "human_review_required_node"
    next_state = _enter_node(state, node_name)
    try:
        next_state["status"] = "human_review"
        next_state["needs_human_review"] = True
        next_state["final_node"] = node_name
        next_state["final_response"] = (
            "The request may be eligible based on the available evidence, "
            "but a human reviewer needs to confirm the decision before any refund action."
        )
        return _trace(
            next_state,
            node_name=node_name,
            event_type="response_prepared",
            message="Prepared human review response.",
            metadata={"risk_level": next_state.get("risk_level"), "refund_amount": next_state.get("refund_amount")},
        )
    except Exception as error:
        next_state["status"] = "escalated"
        next_state["final_node"] = node_name
        next_state["final_response"] = (
            "The request needs manual review before a refund decision can be finalized."
        )
        return _record_error(
            next_state,
            node_name=node_name,
            error=error,
            message="Human review response generation failed",
            status="escalated",
        )


def escalation_response_node(state: RefundDecisionState) -> RefundDecisionState:
    node_name = "escalation_response_node"
    next_state = _enter_node(state, node_name)
    try:
        next_state["status"] = "escalated"
        next_state["needs_human_review"] = True
        next_state["final_node"] = node_name
        next_state["final_response"] = (
            "The available evidence is incomplete or conflicting, so this demo is escalating the request "
            "for manual review instead of making an automatic refund determination."
        )
        return _trace(
            next_state,
            node_name=node_name,
            event_type="response_prepared",
            message="Prepared escalation response.",
            metadata={"errors_present": bool(next_state.get("errors"))},
        )
    except Exception as error:
        next_state["status"] = "escalated"
        next_state["final_node"] = node_name
        next_state["final_response"] = "The request needs manual review."
        return _record_error(
            next_state,
            node_name=node_name,
            error=error,
            message="Escalation response generation failed",
            status="escalated",
        )


def persist_decision_node(state: RefundDecisionState) -> RefundDecisionState:
    node_name = "persist_decision_node"
    next_state = _enter_node(state, node_name)
    lock_path: Path | None = None
    try:
        record = DecisionRecord(
            request_id=str(next_state.get("request_id")),
            customer_id=str(next_state.get("customer_id")),
            refund_eligible=next_state.get("refund_eligible"),
            refund_amount=next_state.get("refund_amount"),
            risk_level=next_state.get("risk_level"),
            needs_human_review=bool(next_state.get("needs_human_review", False)),
            final_node=str(next_state.get("final_node") or "unknown"),
            status=str(next_state.get("status") or "escalated"),
            decision_reason=next_state.get("decision_reason"),
            policy_basis=next_state.get("policy_basis", []),
            evidence_summary=next_state.get("evidence_summary"),
        )
        records_path = Path(DECISION_RECORDS_PATH)
        lock_path = _acquire_persistence_lock(records_path)
        existing_records = _load_persisted_records(records_path)
        existing_records.append(record.model_dump(mode="json"))
        _atomic_write_records(records_path, existing_records)
        next_state["persistence_status"] = "persisted"
        next_state["persistence_record"] = record.model_dump(mode="json")
        return _trace(
            next_state,
            node_name=node_name,
            event_type="decision_persisted",
            message="Persisted refund decision record.",
            metadata={
                "records_path": str(records_path),
                "lock_path": str(lock_path),
                "final_node": record.final_node,
            },
        )
    except Exception as error:
        next_state["persistence_status"] = "failed"
        next_state["persistence_record"] = None
        return _record_error(
            next_state,
            node_name=node_name,
            error=error,
            message="Decision persistence failed",
        )
    finally:
        if lock_path is not None:
            _release_persistence_lock(lock_path)
