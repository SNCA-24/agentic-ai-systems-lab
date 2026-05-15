from app.db import get_connection, init_db
from app.schemas import ApprovalRecord


init_db()


def save_approval_record(record: ApprovalRecord) -> ApprovalRecord:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO approval_records (
                ticket_id,
                approval_status,
                approval_id,
                approved_by,
                approval_notes,
                message,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(ticket_id) DO UPDATE SET
                approval_status = excluded.approval_status,
                approval_id = excluded.approval_id,
                approved_by = excluded.approved_by,
                approval_notes = excluded.approval_notes,
                message = excluded.message,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                record.ticket_id,
                record.approval_status,
                record.approval_id,
                record.approved_by,
                record.approval_notes,
                record.message,
            ),
        )
        connection.commit()

    return record


def get_approval_record(ticket_id: str) -> ApprovalRecord | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                ticket_id,
                approval_status,
                approval_id,
                approved_by,
                approval_notes,
                message
            FROM approval_records
            WHERE ticket_id = ?
            """,
            (ticket_id,),
        ).fetchone()

    if row is None:
        return None

    return ApprovalRecord(
        ticket_id=row["ticket_id"],
        approval_status=row["approval_status"],
        approval_id=row["approval_id"],
        approved_by=row["approved_by"],
        approval_notes=row["approval_notes"],
        message=row["message"],
    )


def clear_approval_store() -> None:
    """
    Test helper for clearing SQLite-backed approval records.
    """
    with get_connection() as connection:
        connection.execute("DELETE FROM approval_records")
        connection.commit()
