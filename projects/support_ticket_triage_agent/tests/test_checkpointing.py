from langgraph.checkpoint.memory import MemorySaver

from app.checkpointing import (
    build_graph_config,
    build_thread_id,
    create_memory_checkpointer,
)
from app.sqlite_action_store import clear_action_store
from app.graph import checkpointed_approval_resume_graph, checkpointed_ticket_graph
from app.state import AgentState


def test_create_memory_checkpointer_returns_memory_saver():
    checkpointer = create_memory_checkpointer()

    assert isinstance(checkpointer, MemorySaver)


def test_build_thread_id_uses_default_prefix():
    thread_id = build_thread_id("TICKET-001")

    assert thread_id == "support-ticket:TICKET-001"


def test_build_thread_id_allows_custom_prefix():
    thread_id = build_thread_id("TICKET-002", prefix="custom-workflow")

    assert thread_id == "custom-workflow:TICKET-002"


def test_build_graph_config_sets_configurable_thread_id():
    config = build_graph_config("support-ticket:TICKET-003")

    assert config == {
        "configurable": {
            "thread_id": "support-ticket:TICKET-003",
        }
    }


def make_state(message: str, ticket_id: str = "CHECKPOINT-001") -> AgentState:
    return {
        "ticket_id": ticket_id,
        "user_message": message,
        "category": None,
        "intent": None,
        "risk_level": None,
        "needs_human_review": False,
        "confidence": None,
        "decision_summary": None,
        "approval_status": "not_required",
        "approval_id": None,
        "approval_notes": None,
        "approved_by": None,
        "workflow_path": [],
        "trace_events": [],
        "tool_results": [],
        "errors": [],
        "final_response": None,
    }


def make_approval_resume_state(
    approval_status: str,
    ticket_id: str = "CHECKPOINT-RESUME-001",
    approval_id: str | None = "approval_checkpoint_001",
    approved_by: str | None = "manager_checkpoint",
) -> AgentState:
    return {
        "ticket_id": ticket_id,
        "user_message": "Resume checkpointed approval workflow.",
        "category": "technical",
        "intent": "high_risk_account_or_financial_action",
        "risk_level": "high",
        "needs_human_review": True,
        "confidence": 0.99,
        "decision_summary": "Checkpointed approval resume test.",
        "approval_status": approval_status,
        "approval_id": approval_id,
        "approval_notes": "Checkpointed approval test notes.",
        "approved_by": approved_by,
        "workflow_path": [],
        "trace_events": [],
        "tool_results": [],
        "errors": [],
        "final_response": None,
    }


def test_checkpointed_ticket_graph_runs_with_thread_id_config_for_billing_ticket():
    thread_id = build_thread_id("CHECKPOINT-001")
    config = build_graph_config(thread_id)
    state = make_state("I was charged twice for my subscription.", ticket_id="CHECKPOINT-001")

    result = checkpointed_ticket_graph.invoke(state, config=config)

    assert result["category"] == "billing"
    assert result["workflow_path"] == [
        "validate_input",
        "classify_ticket",
        "billing_node",
    ]
    assert result["tool_results"][-1]["tool_name"] == "lookup_billing_record"


def test_checkpointed_ticket_graph_runs_with_thread_id_config_for_high_risk_ticket():
    thread_id = build_thread_id("CHECKPOINT-002")
    config = build_graph_config(thread_id)
    state = make_state(
        "Our admin deleted 80 users. Can you restore them immediately?",
        ticket_id="CHECKPOINT-002",
    )

    result = checkpointed_ticket_graph.invoke(state, config=config)

    assert result["risk_level"] == "high"
    assert result["needs_human_review"] is True
    assert result["approval_status"] == "pending"
    assert result["workflow_path"] == [
        "validate_input",
        "classify_ticket",
        "high_risk_review_node",
    ]
    assert result["tool_results"][-1]["tool_name"] == "preview_high_risk_action"
    assert result["tool_results"][-1]["result"]["write_action_executed"] is False


def test_checkpointed_approval_resume_graph_runs_approved_path_with_thread_id_config():
    clear_action_store()
    thread_id = build_thread_id("CHECKPOINT-RESUME-001")
    config = build_graph_config(thread_id)
    state = make_approval_resume_state(
        approval_status="approved",
        ticket_id="CHECKPOINT-RESUME-001",
        approval_id="approval_checkpoint_001",
    )

    result = checkpointed_approval_resume_graph.invoke(state, config=config)

    assert result["workflow_path"] == [
        "approval_resume_entry_node",
        "approval_approved_node",
        "execute_approved_action_node",
    ]
    assert result["approval_status"] == "approved"
    assert result["trace_events"][-1]["event_type"] == "approved_write_tool_completed"
    assert result["tool_results"][-1]["tool_name"] == "execute_approved_high_risk_action"
    assert result["tool_results"][-1]["status"] == "success"
    assert result["tool_results"][-1]["result"]["write_action_executed"] is True
    assert result["tool_results"][-1]["result"]["duplicate_prevented"] is False


def test_checkpointed_approval_resume_graph_runs_rejected_path_with_thread_id_config():
    clear_action_store()
    thread_id = build_thread_id("CHECKPOINT-RESUME-002")
    config = build_graph_config(thread_id)
    state = make_approval_resume_state(
        approval_status="rejected",
        ticket_id="CHECKPOINT-RESUME-002",
        approval_id=None,
        approved_by="manager_checkpoint_reject",
    )

    result = checkpointed_approval_resume_graph.invoke(state, config=config)

    assert result["workflow_path"] == [
        "approval_resume_entry_node",
        "approval_rejected_node",
    ]
    assert result["approval_status"] == "rejected"
    assert result["trace_events"][-1]["event_type"] == "approval_resume_rejected"
    assert result["tool_results"] == []
    assert "blocked" in result["final_response"]