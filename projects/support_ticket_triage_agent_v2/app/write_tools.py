from typing import Literal

from pydantic import BaseModel, Field

from app.sqlite_action_store import get_action_execution, save_action_execution


WriteToolStatus = Literal["success", "failed", "skipped"]


class WriteToolExecutionResult(BaseModel):
    tool_name: str
    status: WriteToolStatus
    result: dict = Field(default_factory=dict)


def execute_approved_high_risk_action(
    ticket_id: str,
    approval_id: str,
    approved_by: str | None,
    idempotency_key: str,
    action_type: str = "simulated_high_risk_action",
) -> WriteToolExecutionResult:
    """
    Simulated approved write tool with idempotency.

    This function represents the shape of a production write tool without calling
    any external system. It records action execution using an idempotency key so
    repeated resume calls do not duplicate the action.
    """
    existing_execution = get_action_execution(idempotency_key)
    if existing_execution is not None:
        return WriteToolExecutionResult(
            tool_name="execute_approved_high_risk_action",
            status="skipped",
            result={
                **existing_execution,
                "duplicate_prevented": True,
                "skip_reason": "idempotency_key_already_executed",
            },
        )

    execution_record = {
        "ticket_id": ticket_id,
        "approval_id": approval_id,
        "approved_by": approved_by,
        "action_type": action_type,
        "idempotency_key": idempotency_key,
        "write_action_executed": True,
        "duplicate_prevented": False,
        "side_effect": "simulated_only",
        "tool_type": "approved_write_simulation",
        "execution_summary": "Approved high-risk action was simulated exactly once.",
    }

    save_action_execution(
        idempotency_key=idempotency_key,
        execution_record=execution_record,
    )

    return WriteToolExecutionResult(
        tool_name="execute_approved_high_risk_action",
        status="success",
        result=execution_record,
    )
