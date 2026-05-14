from fastapi import FastAPI

from app.config import APP_ENV, CLASSIFIER_MODE, LANGSMITH_PROJECT_NAME
from app.graph import ticket_graph
from app.schemas import TriageRequest, TriageResponse
from app.state import AgentState


app = FastAPI(
    title="Support Ticket Triage Agent v2",
    description="Graph-orchestrated support ticket triage agent with risk-aware routing.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "classifier_mode": CLASSIFIER_MODE,
        "environment": APP_ENV,
    }


@app.post("/tickets/triage", response_model=TriageResponse)
def triage_ticket(request: TriageRequest) -> TriageResponse:
    initial_state: AgentState = {
        "ticket_id": request.ticket_id,
        "user_message": request.user_message,
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
        "errors": [],
        "final_response": None,
    }

    config = {
        "run_name": "support_ticket_triage_api_run",
        "tags": [
            "support-ticket-triage",
            "api-run",
            f"classifier:{CLASSIFIER_MODE}",
            f"env:{APP_ENV}",
        ],
        "metadata": {
            "ticket_id": request.ticket_id,
            "classifier_mode": CLASSIFIER_MODE,
            "run_source": "api",
            "environment": APP_ENV,
            "langsmith_project": LANGSMITH_PROJECT_NAME,
        },
    }

    result = ticket_graph.invoke(initial_state, config=config)

    return TriageResponse(
        ticket_id=result["ticket_id"],
        category=result["category"],
        intent=result["intent"],
        risk_level=result["risk_level"],
        needs_human_review=result["needs_human_review"],
        confidence=result["confidence"],
        decision_summary=result["decision_summary"],
        workflow_path=result["workflow_path"],
        trace_events_count=len(result.get("trace_events", [])),
        final_response=result["final_response"],
        errors=result["errors"],
    )