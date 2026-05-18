

"""
Demo: true interrupt-style HITL pause/resume flow.

Run from the project folder:

    python scripts/demo_interruptible_graph.py

This demo does not call OpenAI when CLASSIFIER_MODE=mock. It shows how a
high-risk support ticket pauses at a LangGraph interrupt and later resumes with
Command(resume=...).
"""

from pathlib import Path
from pprint import pprint
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langgraph.types import Command

from app.checkpointing import build_graph_config, build_thread_id
from app.graph import interruptible_ticket_graph
from app.sqlite_action_store import clear_action_store
from app.state import AgentState


def make_state(ticket_id: str, user_message: str) -> AgentState:
    return {
        "ticket_id": ticket_id,
        "user_message": user_message,
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


def main() -> None:
    ticket_id = "DEMO-INTERRUPT-001"
    user_message = "Our admin deleted 80 users. Can you restore them immediately?"

    clear_action_store()

    thread_id = build_thread_id(ticket_id)
    config = build_graph_config(thread_id)
    state = make_state(ticket_id=ticket_id, user_message=user_message)

    print("\n=== Demo: Interruptible HITL Graph ===")
    print(f"ticket_id: {ticket_id}")
    print(f"thread_id: {thread_id}")
    print(f"user_message: {user_message}")

    print("\n--- Step 1: Invoke graph until human approval interrupt ---")
    interrupted_result = interruptible_ticket_graph.invoke(state, config=config)

    if "__interrupt__" not in interrupted_result:
        raise RuntimeError("Expected graph to interrupt for this high-risk ticket.")

    interrupt_payload = interrupted_result["__interrupt__"][0].value
    pprint(interrupt_payload)

    print("\n--- Step 2: Resume same graph thread with approval decision ---")
    approval_payload = {
        "approved": True,
        "approval_id": "approval_demo_interrupt_001",
        "approved_by": "demo_manager",
        "approval_notes": "Demo approval for interruptible workflow.",
    }

    resumed_result = interruptible_ticket_graph.invoke(
        Command(resume=approval_payload),
        config=config,
    )

    print("\n--- Final workflow path ---")
    pprint(resumed_result["workflow_path"])

    print("\n--- Final approval status ---")
    pprint(
        {
            "approval_status": resumed_result["approval_status"],
            "approval_id": resumed_result["approval_id"],
            "approved_by": resumed_result["approved_by"],
        }
    )

    print("\n--- Last tool result ---")
    pprint(resumed_result["tool_results"][-1])

    print("\n--- Final response ---")
    print(resumed_result["final_response"])


if __name__ == "__main__":
    main()