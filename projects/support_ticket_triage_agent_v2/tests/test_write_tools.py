

from app.action_store import build_idempotency_key, clear_action_store, get_action_execution
from app.write_tools import execute_approved_high_risk_action


def setup_function():
    clear_action_store()


def test_execute_approved_high_risk_action_executes_once():
    idempotency_key = build_idempotency_key(
        ticket_id="TICKET-001",
        approval_id="APPROVAL-001",
        action_type="simulated_high_risk_action",
    )

    result = execute_approved_high_risk_action(
        ticket_id="TICKET-001",
        approval_id="APPROVAL-001",
        approved_by="manager_001",
        idempotency_key=idempotency_key,
    )

    assert result.tool_name == "execute_approved_high_risk_action"
    assert result.status == "success"
    assert result.result["ticket_id"] == "TICKET-001"
    assert result.result["approval_id"] == "APPROVAL-001"
    assert result.result["approved_by"] == "manager_001"
    assert result.result["idempotency_key"] == idempotency_key
    assert result.result["write_action_executed"] is True
    assert result.result["duplicate_prevented"] is False
    assert result.result["side_effect"] == "simulated_only"
    assert result.result["tool_type"] == "approved_write_simulation"

    stored_execution = get_action_execution(idempotency_key)
    assert stored_execution is not None
    assert stored_execution["write_action_executed"] is True


def test_execute_approved_high_risk_action_prevents_duplicate_execution():
    idempotency_key = build_idempotency_key(
        ticket_id="TICKET-002",
        approval_id="APPROVAL-002",
        action_type="simulated_high_risk_action",
    )

    first_result = execute_approved_high_risk_action(
        ticket_id="TICKET-002",
        approval_id="APPROVAL-002",
        approved_by="manager_002",
        idempotency_key=idempotency_key,
    )
    second_result = execute_approved_high_risk_action(
        ticket_id="TICKET-002",
        approval_id="APPROVAL-002",
        approved_by="manager_002",
        idempotency_key=idempotency_key,
    )

    assert first_result.status == "success"
    assert first_result.result["write_action_executed"] is True
    assert first_result.result["duplicate_prevented"] is False

    assert second_result.status == "skipped"
    assert second_result.result["write_action_executed"] is True
    assert second_result.result["duplicate_prevented"] is True
    assert second_result.result["skip_reason"] == "idempotency_key_already_executed"


def test_execute_approved_high_risk_action_allows_custom_action_type():
    idempotency_key = build_idempotency_key(
        ticket_id="TICKET-003",
        approval_id="APPROVAL-003",
        action_type="restore_deleted_users",
    )

    result = execute_approved_high_risk_action(
        ticket_id="TICKET-003",
        approval_id="APPROVAL-003",
        approved_by="manager_003",
        idempotency_key=idempotency_key,
        action_type="restore_deleted_users",
    )

    assert result.status == "success"
    assert result.result["action_type"] == "restore_deleted_users"
    assert result.result["idempotency_key"] == idempotency_key
    assert result.result["write_action_executed"] is True