from pathlib import Path

from app.policy_store import PolicyStore, retrieve_policy_documents
from app.tracing import add_trace_event, append_workflow_path


PROJECT_DIR = Path(__file__).resolve().parents[1]
POLICY_DIR = PROJECT_DIR / "data" / "policies"


def _read_policy(name: str) -> str:
    return (POLICY_DIR / name).read_text(encoding="utf-8")


def test_policy_files_exist_and_are_non_empty():
    for policy_name in (
        "refund_policy.md",
        "cancellation_policy.md",
        "billing_policy.md",
    ):
        policy_path = POLICY_DIR / policy_name
        assert policy_path.exists()
        assert policy_path.read_text(encoding="utf-8").strip()


def test_refund_policy_covers_required_milestone_1_topics():
    policy = _read_policy("refund_policy.md").lower()

    assert "duplicate charge" in policy
    assert "refund window" in policy
    assert "30-day" in policy or "30 day" in policy
    assert "high-value" in policy or "high value" in policy
    assert "$100.00" in policy or "$100" in policy or "100.00" in policy
    assert "enterprise" in policy
    assert "human review" in policy
    assert "conflicting evidence" in policy or "unclear evidence" in policy
    assert "escalat" in policy


def test_cancellation_policy_covers_post_cancellation_charges_and_escalation():
    policy = _read_policy("cancellation_policy.md").lower()

    assert "cancellation timestamp" in policy
    assert "charged after cancellation" in policy or "charge after cancellation" in policy
    assert "pending" in policy
    assert "finalized" in policy
    assert "refund" in policy
    assert "conflicting evidence" in policy or "unclear evidence" in policy
    assert "escalat" in policy


def test_billing_policy_covers_duplicate_detection_and_review_boundaries():
    policy = _read_policy("billing_policy.md").lower()

    assert "duplicate charge" in policy
    assert "invoice" in policy
    assert "recurring subscription" in policy
    assert "annual" in policy
    assert "enterprise" in policy
    assert "high-value" in policy or "high value" in policy
    assert "human review" in policy
    assert "conflicting evidence" in policy or "unclear evidence" in policy


def test_duplicate_charge_query_returns_duplicate_charge_guidance():
    documents = retrieve_policy_documents(
        "I was charged twice for the same invoice and think this is a duplicate charge.",
        intent="duplicate_charge_refund",
    )

    assert documents
    assert any("duplicate charge" in document.section_title.lower() or "duplicate charge" in document.content.lower() for document in documents)
    assert any(document.source == "billing_policy.md" for document in documents)


def test_unclear_evidence_query_returns_escalation_guidance():
    store = PolicyStore(POLICY_DIR)

    documents = store.search(
        "The cancellation date and billing records do not line up and I may be missing evidence.",
        intent="unclear_refund_request",
    )

    assert documents
    assert any("escalat" in document.content.lower() or "evidence" in document.section_title.lower() for document in documents)
    assert any(document.source in {"refund_policy.md", "cancellation_policy.md"} for document in documents)


def test_retrieved_documents_include_source_metadata_and_section_refs():
    store = PolicyStore(POLICY_DIR)

    documents = store.search(
        "refund window for duplicate charge",
        intent="duplicate_charge_refund",
        limit=2,
    )

    assert documents
    for document in documents:
        assert document.source.endswith(".md")
        assert document.section_title
        assert document.section_ref.startswith(document.source.removesuffix(".md"))
        assert 0.0 <= document.score <= 1.0
        assert document.content


def test_tracing_helpers_append_path_and_events_deterministically():
    workflow_path = ["validate_input_node"]
    trace_events = []

    updated_path = append_workflow_path(workflow_path, "retrieve_policy_context_node")
    updated_events = add_trace_event(
        trace_events,
        "retrieve_policy_context_node",
        "policy_retrieval_completed",
        "Retrieved refund policy context.",
        metadata={"sources": ["billing_policy.md", "refund_policy.md"], "doc_count": 2},
    )

    assert workflow_path == ["validate_input_node"]
    assert updated_path == ["validate_input_node", "retrieve_policy_context_node"]

    assert trace_events == []
    assert updated_events == [
        {
            "node": "retrieve_policy_context_node",
            "event_type": "policy_retrieval_completed",
            "message": "Retrieved refund policy context.",
            "metadata": {
                "doc_count": 2,
                "sources": ["billing_policy.md", "refund_policy.md"],
            },
        }
    ]
