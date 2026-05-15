

from langgraph.types import Command

from app.checkpointing import build_graph_config, build_thread_id
from app.graph import interruptible_ticket_graph
from app.sqlite_action_store import clear_action_store
from app.state import AgentState


def setup_function():
    clear_action_store()


def make_state(message: str, ticket_id: str = "INTERRUPT-001") -> AgentState:
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


def test_interruptible_graph_normal_billing_ticket_completes_without_interrupt():
    thread_id = build_thread_id("INTERRUPT-001")
    config = build_graph_config(thread_id)
    state = make_state(
        "I was charged twice for my subscription.",
        ticket_id="INTERRUPT-001",
    )

    result = interruptible_ticket_graph.invoke(state, config=config)

    assert "__interrupt__" not in result
    assert result["category"] == "billing"
    assert result["approval_status"] == "not_required"
    assert result["workflow_path"] == [
        "validate_input",
        "classify_ticket",
        "billing_node",
    ]
    assert result["tool_results"][-1]["tool_name"] == "lookup_billing_record"


def test_interruptible_graph_high_risk_ticket_pauses_for_human_approval():
    thread_id = build_thread_id("INTERRUPT-002")
    config = build_graph_config(thread_id)
    state = make_state(
        "Our admin deleted 80 users. Can you restore them immediately?",
        ticket_id="INTERRUPT-002",
    )

    result = interruptible_ticket_graph.invoke(state, config=config)

    assert "__interrupt__" in result
    interrupt_payload = result["__interrupt__"][0].value
    assert interrupt_payload["ticket_id"] == "INTERRUPT-002"
    assert interrupt_payload["approval_status"] == "pending"
    assert interrupt_payload["approval_required"] is True
    assert interrupt_payload["risk_level"] == "high"
    assert interrupt_payload["action_preview"]["tool_name"] == "preview_high_risk_action"
    assert interrupt_payload["action_preview"]["result"]["write_action_executed"] is False


def test_interruptible_graph_approved_resume_executes_simulated_write_tool_once():
    thread_id = build_thread_id("INTERRUPT-003")
    config = build_graph_config(thread_id)
    state = make_state(
        "Our admin deleted 80 users. Can you restore them immediately?",
        ticket_id="INTERRUPT-003",
    )

    first_result = interruptible_ticket_graph.invoke(state, config=config)
    assert "__interrupt__" in first_result

    resumed_result = interruptible_ticket_graph.invoke(
        Command(
            resume={
                "approved": True,
                "approval_id": "approval_interrupt_003",
                "approved_by": "manager_interrupt",
                "approval_notes": "Approved for interruptible workflow test.",
            }
        ),
        config=config,
    )

    assert resumed_result["workflow_path"] == [
        "validate_input",
        "classify_ticket",
        "high_risk_review_node",
        "human_approval_interrupt_node",
        "approval_approved_node",
        "execute_approved_action_node",
    ]
    assert resumed_result["approval_status"] == "approved"
    assert resumed_result["approval_id"] == "approval_interrupt_003"
    assert resumed_result["approved_by"] == "manager_interrupt"
    assert resumed_result["trace_events"][-1]["event_type"] == "approved_write_tool_completed"
    assert resumed_result["tool_results"][-1]["tool_name"] == "execute_approved_high_risk_action"
    assert resumed_result["tool_results"][-1]["status"] == "success"
    assert resumed_result["tool_results"][-1]["result"]["write_action_executed"] is True
    assert resumed_result["tool_results"][-1]["result"]["duplicate_prevented"] is False


def test_interruptible_graph_rejected_resume_blocks_without_write_tool_execution():
    thread_id = build_thread_id("INTERRUPT-004")
    config = build_graph_config(thread_id)
    state = make_state(
        "Our admin deleted 80 users. Can you restore them immediately?",
        ticket_id="INTERRUPT-004",
    )

    first_result = interruptible_ticket_graph.invoke(state, config=config)
    assert "__interrupt__" in first_result

    resumed_result = interruptible_ticket_graph.invoke(
        Command(
            resume={
                "approved": False,
                "approved_by": "manager_interrupt",
                "approval_notes": "Rejected for interruptible workflow test.",
            }
        ),
        config=config,
    )

    assert resumed_result["workflow_path"] == [
        "validate_input",
        "classify_ticket",
        "high_risk_review_node",
        "human_approval_interrupt_node",
        "approval_rejected_node",
    ]
    assert resumed_result["approval_status"] == "rejected"
    assert resumed_result["trace_events"][-1]["event_type"] == "approval_resume_rejected"
    assert resumed_result["tool_results"][-1]["tool_name"] == "preview_high_risk_action"
    assert resumed_result["tool_results"][-1]["result"]["write_action_executed"] is False
    assert "blocked" in resumed_result["final_response"]