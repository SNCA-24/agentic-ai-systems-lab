from fastapi import FastAPI, HTTPException

from app.config import APP_ENV, CLASSIFIER_MODE, LANGSMITH_PROJECT_NAME
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


approval_store: dict[str, ApprovalRecord] = {}


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
        approval_status=result["approval_status"],
        confidence=result["confidence"],
        decision_summary=result["decision_summary"],
        workflow_path=result["workflow_path"],
        trace_events_count=len(result.get("trace_events", [])),
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
            message="Approval recorded. Workflow resume is not implemented yet.",
        )
        approval_store[ticket_id] = record
        return ApprovalResponse(**record.model_dump())

    record = ApprovalRecord(
        ticket_id=ticket_id,
        approval_status="rejected",
        approval_id=request.approval_id,
        approved_by=request.approved_by,
        approval_notes=request.approval_notes,
        message="Approval rejected. No write action has been executed.",
    )
    approval_store[ticket_id] = record
    return ApprovalResponse(**record.model_dump())


@app.get("/tickets/{ticket_id}/approval", response_model=ApprovalRecord)
def get_approval(ticket_id: str) -> ApprovalRecord:
    """
    Return the latest human approval decision for a ticket.

    Current implementation uses an in-memory development store.
    Durable storage will be added in a later step.
    """
    record = approval_store.get(ticket_id)
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

    Current implementation uses the in-memory approval store and a safe resume graph.
    It does not execute any real write action.
    """
    record = approval_store.get(ticket_id)
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

    return ResumeResponse(
        ticket_id=result["ticket_id"],
        approval_status=result["approval_status"],
        approval_id=result["approval_id"],
        approved_by=result["approved_by"],
        workflow_path=result["workflow_path"],
        trace_events_count=len(result.get("trace_events", [])),
        final_response=result["final_response"],
        errors=result["errors"],
    )