from fastapi import FastAPI, HTTPException

from app.config import APP_ENV, CLASSIFIER_MODE, LANGSMITH_PROJECT_NAME
from app.sqlite_approval_store import get_approval_record, save_approval_record
from app.graph import approval_resume_graph, ticket_graph
from app.schemas import (
    ApprovalRecord,
    ApprovalRequest,
    ApprovalResponse,
    ResumeResponse,
    TriageRequest,
    TriageResponse,
)
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
        "tool_results": [],
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
        approval_status=result["approval_status"],
        confidence=result["confidence"],
        decision_summary=result["decision_summary"],
        workflow_path=result["workflow_path"],
        trace_events_count=len(result.get("trace_events", [])),
        tool_results_count=len(result.get("tool_results", [])),
        final_response=result["final_response"],
        errors=result["errors"],
    )


@app.post("/tickets/{ticket_id}/approval", response_model=ApprovalResponse)
def record_approval(ticket_id: str, request: ApprovalRequest) -> ApprovalResponse:
    """
    Record a human approval decision for a high-risk ticket.

    This endpoint intentionally does not resume graph execution yet.
    Durable workflow resume/checkpointing will be added in a later step.
    """
    if request.approved:
        if not request.approval_id:
            return ApprovalResponse(
                ticket_id=ticket_id,
                approval_status="rejected",
                approval_id=None,
                approved_by=request.approved_by,
                approval_notes=request.approval_notes,
                message="Approval was not accepted because approval_id is required when approved is true.",
            )

        record = ApprovalRecord(
            ticket_id=ticket_id,
            approval_status="approved",
            approval_id=request.approval_id,
            approved_by=request.approved_by,
            approval_notes=request.approval_notes,
            message="Approval recorded. Workflow can now be resumed safely.",
        )

        saved_record = save_approval_record(record)
        return ApprovalResponse(**saved_record.model_dump())

    record = ApprovalRecord(
        ticket_id=ticket_id,
        approval_status="rejected",
        approval_id=request.approval_id,
        approved_by=request.approved_by,
        approval_notes=request.approval_notes,
        message="Approval rejected. No write action has been executed.",
    )

    saved_record = save_approval_record(record)
    return ApprovalResponse(**saved_record.model_dump())


@app.get("/tickets/{ticket_id}/approval", response_model=ApprovalRecord)
def get_approval(ticket_id: str) -> ApprovalRecord:
    """
    Return the latest human approval decision for a ticket.

    Current implementation uses a SQLite-backed approval store.
    Durable LangGraph checkpointing will be added in a later step.
    """
    record = get_approval_record(ticket_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No approval decision found for ticket_id={ticket_id}.",
        )

    return record


@app.post("/tickets/{ticket_id}/resume", response_model=ResumeResponse)
def resume_ticket(ticket_id: str) -> ResumeResponse:
    """
    Resume a high-risk workflow from the latest approval decision.

    Current implementation uses the SQLite-backed approval store and a safe resume graph.
    It executes only a simulated approved write action with idempotency protection.
    """
    record = get_approval_record(ticket_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot resume ticket_id={ticket_id} because no approval decision was found.",
        )

    initial_state: AgentState = {
        "ticket_id": ticket_id,
        "user_message": "Resume high-risk workflow after approval decision.",
        "category": "technical",
        "intent": "high_risk_account_or_financial_action",
        "risk_level": "high",
        "needs_human_review": True,
        "confidence": 0.99,
        "decision_summary": "High-risk workflow resume requested after human approval decision.",
        "approval_status": record.approval_status,
        "approval_id": record.approval_id,
        "approval_notes": record.approval_notes,
        "approved_by": record.approved_by,
        "workflow_path": [],
        "trace_events": [],
        "tool_results": [],
        "errors": [],
        "final_response": None,
    }

    config = {
        "run_name": "support_ticket_triage_resume_run",
        "tags": [
            "support-ticket-triage",
            "resume-run",
            f"classifier:{CLASSIFIER_MODE}",
            f"env:{APP_ENV}",
        ],
        "metadata": {
            "ticket_id": ticket_id,
            "approval_status": record.approval_status,
            "approval_id": record.approval_id,
            "approved_by": record.approved_by,
            "run_source": "resume_api",
            "environment": APP_ENV,
            "langsmith_project": LANGSMITH_PROJECT_NAME,
        },
    }

    result = approval_resume_graph.invoke(initial_state, config=config)
    tool_results = result.get("tool_results", [])
    last_tool_result = tool_results[-1] if tool_results else None

    return ResumeResponse(
        ticket_id=result["ticket_id"],
        approval_status=result["approval_status"],
        approval_id=result["approval_id"],
        approved_by=result["approved_by"],
        workflow_path=result["workflow_path"],
        trace_events_count=len(result.get("trace_events", [])),
        tool_results_count=len(tool_results),
        last_tool_result=last_tool_result,
        final_response=result["final_response"],
        errors=result["errors"],
    )