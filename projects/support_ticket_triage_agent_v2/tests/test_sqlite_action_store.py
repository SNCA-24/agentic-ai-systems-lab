from app.sqlite_action_store import (
    build_idempotency_key,
    clear_action_store,
    get_action_execution,
    save_action_execution,
)


def setup_function():
    clear_action_store()


def test_build_idempotency_key_uses_ticket_approval_and_action_type():
    key = build_idempotency_key(
        ticket_id="SQLITE-ACTION-001",
        approval_id="APPROVAL-001",
        action_type="simulated_high_risk_action",
    )

    assert key == "SQLITE-ACTION-001:APPROVAL-001:simulated_high_risk_action"


def test_get_action_execution_returns_none_when_missing():
    result = get_action_execution("missing-idempotency-key")

    assert result is None


def test_save_and_get_action_execution_round_trip():
    idempotency_key = build_idempotency_key(
        ticket_id="SQLITE-ACTION-002",
        approval_id="APPROVAL-002",
        action_type="simulated_high_risk_action",
    )
    execution_record = {
        "ticket_id": "SQLITE-ACTION-002",
        "approval_id": "APPROVAL-002",
        "approved_by": "manager_002",
        "action_type": "simulated_high_risk_action",
        "idempotency_key": idempotency_key,
        "write_action_executed": True,
        "duplicate_prevented": False,
        "side_effect": "simulated_only",
        "tool_type": "approved_write_simulation",
        "execution_summary": "Approved high-risk action was simulated exactly once.",
    }

    saved = save_action_execution(
        idempotency_key=idempotency_key,
        execution_record=execution_record,
    )
    loaded = get_action_execution(idempotency_key)

    assert saved == execution_record
    assert loaded == execution_record


def test_save_action_execution_updates_existing_idempotency_key():
    idempotency_key = build_idempotency_key(
        ticket_id="SQLITE-ACTION-003",
        approval_id="APPROVAL-003",
        action_type="simulated_high_risk_action",
    )
    original = {
        "ticket_id": "SQLITE-ACTION-003",
        "approval_id": "APPROVAL-003",
        "approved_by": "manager_003",
        "action_type": "simulated_high_risk_action",
        "idempotency_key": idempotency_key,
        "write_action_executed": True,
        "duplicate_prevented": False,
        "side_effect": "simulated_only",
        "tool_type": "approved_write_simulation",
        "execution_summary": "Original execution summary.",
    }
    updated = {
        **original,
        "duplicate_prevented": True,
        "execution_summary": "Updated execution summary.",
    }

    save_action_execution(idempotency_key=idempotency_key, execution_record=original)
    save_action_execution(idempotency_key=idempotency_key, execution_record=updated)
    loaded = get_action_execution(idempotency_key)

    assert loaded == updated


def test_clear_action_store_removes_saved_execution():
    idempotency_key = build_idempotency_key(
        ticket_id="SQLITE-ACTION-004",
        approval_id="APPROVAL-004",
        action_type="simulated_high_risk_action",
    )
    execution_record = {
        "ticket_id": "SQLITE-ACTION-004",
        "approval_id": "APPROVAL-004",
        "approved_by": "manager_004",
        "action_type": "simulated_high_risk_action",
        "idempotency_key": idempotency_key,
        "write_action_executed": True,
        "duplicate_prevented": False,
        "side_effect": "simulated_only",
        "tool_type": "approved_write_simulation",
        "execution_summary": "Execution before clearing.",
    }

    save_action_execution(idempotency_key=idempotency_key, execution_record=execution_record)
    assert get_action_execution(idempotency_key) is not None

    clear_action_store()

    assert get_action_execution(idempotency_key) is None