from app.schemas import ApprovalRecord
from app.sqlite_approval_store import (
    clear_approval_store,
    get_approval_record,
    save_approval_record,
)


def setup_function():
    clear_approval_store()


def test_get_approval_record_returns_none_when_missing():
    record = get_approval_record("missing-ticket")

    assert record is None


def test_save_and_get_approved_record_round_trip():
    record = ApprovalRecord(
        ticket_id="SQLITE-001",
        approval_status="approved",
        approval_id="approval_sqlite_001",
        approved_by="manager_001",
        approval_notes="Approved for SQLite test.",
        message="Approval recorded. Workflow can now be resumed safely.",
    )

    saved = save_approval_record(record)
    loaded = get_approval_record("SQLITE-001")

    assert saved == record
    assert loaded == record


def test_save_and_get_rejected_record_round_trip():
    record = ApprovalRecord(
        ticket_id="SQLITE-002",
        approval_status="rejected",
        approval_id=None,
        approved_by="manager_002",
        approval_notes="Rejected for SQLite test.",
        message="Approval rejected. No write action has been executed.",
    )

    save_approval_record(record)
    loaded = get_approval_record("SQLITE-002")

    assert loaded is not None
    assert loaded.ticket_id == "SQLITE-002"
    assert loaded.approval_status == "rejected"
    assert loaded.approval_id is None
    assert loaded.approved_by == "manager_002"
    assert loaded.approval_notes == "Rejected for SQLite test."


def test_save_approval_record_updates_existing_ticket():
    original = ApprovalRecord(
        ticket_id="SQLITE-003",
        approval_status="rejected",
        approval_id=None,
        approved_by="manager_003",
        approval_notes="Initial rejection.",
        message="Approval rejected. No write action has been executed.",
    )
    updated = ApprovalRecord(
        ticket_id="SQLITE-003",
        approval_status="approved",
        approval_id="approval_sqlite_003",
        approved_by="manager_004",
        approval_notes="Updated to approved after review.",
        message="Approval recorded. Workflow can now be resumed safely.",
    )

    save_approval_record(original)
    save_approval_record(updated)
    loaded = get_approval_record("SQLITE-003")

    assert loaded == updated


def test_clear_approval_store_removes_saved_records():
    record = ApprovalRecord(
        ticket_id="SQLITE-004",
        approval_status="approved",
        approval_id="approval_sqlite_004",
        approved_by="manager_004",
        approval_notes="Approved before clearing.",
        message="Approval recorded. Workflow can now be resumed safely.",
    )

    save_approval_record(record)
    assert get_approval_record("SQLITE-004") is not None

    clear_approval_store()

    assert get_approval_record("SQLITE-004") is None
