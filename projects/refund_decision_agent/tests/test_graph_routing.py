from __future__ import annotations

import importlib
import sys
import types

import pytest

langgraph = pytest.importorskip("langgraph")
del langgraph


@pytest.fixture
def refund_modules(monkeypatch: pytest.MonkeyPatch):
    existing_dotenv = sys.modules.get("dotenv")
    if existing_dotenv is not None:
        if not hasattr(existing_dotenv, "load_dotenv"):
            monkeypatch.setattr(
                existing_dotenv,
                "load_dotenv",
                lambda *args, **kwargs: None,
                raising=False,
            )
    else:
        try:
            importlib.import_module("dotenv")
        except ModuleNotFoundError:
            monkeypatch.setitem(
                sys.modules,
                "dotenv",
                types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None),
            )

    nodes = importlib.import_module("app.nodes")
    graph = importlib.import_module("app.graph")
    state = importlib.import_module("app.state")
    return nodes, graph, state


def _invoke_graph(
    *,
    customer_id: str,
    user_message: str,
    request_id: str,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    refund_modules,
):
    nodes, graph, _state_module = refund_modules
    records_path = tmp_path / "decision_records.json"
    records_path.write_text("[]\n", encoding="utf-8")
    monkeypatch.setattr(nodes, "DECISION_RECORDS_PATH", records_path)

    initial_state = graph.create_initial_state(
        request_id=request_id,
        customer_id=customer_id,
        user_message=user_message,
    )

    return graph.refund_decision_graph.invoke(initial_state)


@pytest.mark.parametrize(
    ("customer_id", "user_message", "expected_final_node"),
    [
        (
            "cust_001",
            "I was charged twice for the same invoice and need a refund.",
            "eligible_response_node",
        ),
        (
            "cust_002",
            "I was billed after cancellation and want a refund.",
            "eligible_response_node",
        ),
    ],
)
def test_eligible_scenarios_route_through_persist(
    customer_id: str,
    user_message: str,
    expected_final_node: str,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    refund_modules,
):
    result = _invoke_graph(
        customer_id=customer_id,
        user_message=user_message,
        request_id=f"REQ-{customer_id}",
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        refund_modules=refund_modules,
    )

    assert result["final_node"] == expected_final_node
    assert result["persistence_status"] == "persisted"
    assert result["workflow_path"] == [
        "validate_input_node",
        "classify_refund_request_node",
        "retrieve_policy_context_node",
        "lookup_billing_evidence_node",
        "decide_refund_eligibility_node",
        "eligible_response_node",
        "persist_decision_node",
    ]


def test_outside_window_routes_to_ineligible_then_persist(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    refund_modules,
):
    result = _invoke_graph(
        customer_id="cust_003",
        user_message="I want a refund even though this charge is outside the refund window.",
        request_id="REQ-cust_003",
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        refund_modules=refund_modules,
    )

    assert result["final_node"] == "ineligible_response_node"
    assert result["persistence_status"] == "persisted"
    assert result["workflow_path"] == [
        "validate_input_node",
        "classify_refund_request_node",
        "retrieve_policy_context_node",
        "lookup_billing_evidence_node",
        "decide_refund_eligibility_node",
        "ineligible_response_node",
        "persist_decision_node",
    ]


def test_enterprise_high_value_routes_to_human_review_then_persist(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    refund_modules,
):
    result = _invoke_graph(
        customer_id="cust_004",
        user_message="I need a refund for my enterprise annual account.",
        request_id="REQ-cust_004",
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        refund_modules=refund_modules,
    )

    assert result["final_node"] == "human_review_required_node"
    assert result["persistence_status"] == "persisted"
    assert result["workflow_path"] == [
        "validate_input_node",
        "classify_refund_request_node",
        "retrieve_policy_context_node",
        "lookup_billing_evidence_node",
        "decide_refund_eligibility_node",
        "human_review_required_node",
        "persist_decision_node",
    ]


def test_conflicting_evidence_routes_deterministically_then_persists(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    refund_modules,
):
    result = _invoke_graph(
        customer_id="cust_005",
        user_message="The evidence is conflicting and I need help with this refund.",
        request_id="REQ-cust_005",
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        refund_modules=refund_modules,
    )

    assert result["final_node"] == "human_review_required_node"
    assert result["persistence_status"] == "persisted"
    assert result["workflow_path"] == [
        "validate_input_node",
        "classify_refund_request_node",
        "retrieve_policy_context_node",
        "lookup_billing_evidence_node",
        "decide_refund_eligibility_node",
        "human_review_required_node",
        "persist_decision_node",
    ]


def test_missing_customer_routes_to_escalation_then_persist(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    refund_modules,
):
    result = _invoke_graph(
        customer_id="cust_missing",
        user_message="I need a refund for a charge on my missing account.",
        request_id="REQ-cust_missing",
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        refund_modules=refund_modules,
    )

    assert result["final_node"] == "escalation_response_node"
    assert result["persistence_status"] == "persisted"
    assert result["workflow_path"] == [
        "validate_input_node",
        "classify_refund_request_node",
        "retrieve_policy_context_node",
        "lookup_billing_evidence_node",
        "decide_refund_eligibility_node",
        "escalation_response_node",
        "persist_decision_node",
    ]


def test_validation_failure_routes_to_escalation_then_persist(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    refund_modules,
):
    result = _invoke_graph(
        customer_id="cust_001",
        user_message="   ",
        request_id="REQ-validation-failure",
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        refund_modules=refund_modules,
    )

    assert result["final_node"] == "escalation_response_node"
    assert result["persistence_status"] == "persisted"
    assert result["workflow_path"] == [
        "validate_input_node",
        "escalation_response_node",
        "persist_decision_node",
    ]
