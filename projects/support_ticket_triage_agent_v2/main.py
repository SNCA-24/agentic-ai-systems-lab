from app.config import APP_ENV, CLASSIFIER_MODE, LANGSMITH_PROJECT_NAME
from app.graph import ticket_graph
from app.state import AgentState


def run_ticket(ticket_id: str, user_message: str):
    initial_state: AgentState = {
        "ticket_id": ticket_id,
        "user_message": user_message,
        "category": None,
        "intent": None,
        "risk_level": None,
        "needs_human_review": False,
        "confidence": None,
        "decision_summary": None,
        "workflow_path": [],
        "trace_events": [],
        "errors": [],
        "final_response": None,
    }

    config = {
        "run_name": "support_ticket_triage_demo_run",
        "tags": [
            "support-ticket-triage",
            "demo-run",
            f"classifier:{CLASSIFIER_MODE}",
            f"env:{APP_ENV}",
        ],
        "metadata": {
            "ticket_id": ticket_id,
            "classifier_mode": CLASSIFIER_MODE,
            "run_source": "main",
            "environment": APP_ENV,
            "langsmith_project": LANGSMITH_PROJECT_NAME,
        },
    }

    result = ticket_graph.invoke(initial_state, config=config)
    return result


if __name__ == "__main__":
    examples = [
        ("TICKET-001", "My app keeps crashing whenever I upload a PDF."),
        ("TICKET-002", "I was charged twice for my subscription."),
        ("TICKET-003", "Our admin deleted 80 users. Can you restore them immediately?"),
        ("TICKET-004", "How do I change my profile picture?"),
        ("TICKET-005", "Please give this employee admin access immediately."),
    ]

    for ticket_id, message in examples:
        result = run_ticket(ticket_id, message)

        print("\n---")
        print("Ticket:", ticket_id)
        print("Classifier mode:", CLASSIFIER_MODE)
        print("Message:", message)
        print("Category:", result["category"])
        print("Intent:", result["intent"])
        print("Risk:", result["risk_level"])
        print("Needs review:", result["needs_human_review"])
        print("Confidence:", result["confidence"])
        print("Decision summary:", result["decision_summary"])
        print("Workflow path:", result["workflow_path"])
        print("Trace events:", result["trace_events"])
        print("Response:", result["final_response"])
        print("Errors:", result["errors"])