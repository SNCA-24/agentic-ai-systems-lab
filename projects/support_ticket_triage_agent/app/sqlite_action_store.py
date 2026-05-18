import json
from typing import Any

from app.db import get_connection, init_db


init_db()


def build_idempotency_key(
    ticket_id: str,
    approval_id: str,
    action_type: str,
) -> str:
    return f"{ticket_id}:{approval_id}:{action_type}"


def get_action_execution(idempotency_key: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT raw_result_json
            FROM action_execution_records
            WHERE idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()

    if row is None:
        return None

    return json.loads(row["raw_result_json"])


def save_action_execution(
    idempotency_key: str,
    execution_record: dict[str, Any],
) -> dict[str, Any]:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO action_execution_records (
                idempotency_key,
                ticket_id,
                approval_id,
                approved_by,
                action_type,
                write_action_executed,
                duplicate_prevented,
                side_effect,
                tool_type,
                execution_summary,
                raw_result_json,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(idempotency_key) DO UPDATE SET
                ticket_id = excluded.ticket_id,
                approval_id = excluded.approval_id,
                approved_by = excluded.approved_by,
                action_type = excluded.action_type,
                write_action_executed = excluded.write_action_executed,
                duplicate_prevented = excluded.duplicate_prevented,
                side_effect = excluded.side_effect,
                tool_type = excluded.tool_type,
                execution_summary = excluded.execution_summary,
                raw_result_json = excluded.raw_result_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                idempotency_key,
                execution_record["ticket_id"],
                execution_record["approval_id"],
                execution_record.get("approved_by"),
                execution_record["action_type"],
                int(execution_record["write_action_executed"]),
                int(execution_record["duplicate_prevented"]),
                execution_record["side_effect"],
                execution_record["tool_type"],
                execution_record["execution_summary"],
                json.dumps(execution_record, sort_keys=True),
            ),
        )
        connection.commit()

    return execution_record


def clear_action_store() -> None:
    """
    Test helper for clearing SQLite-backed action execution records.
    """
    with get_connection() as connection:
        connection.execute("DELETE FROM action_execution_records")
        connection.commit()