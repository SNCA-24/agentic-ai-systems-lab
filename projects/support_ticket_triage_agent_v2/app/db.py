import sqlite3
from pathlib import Path
from sqlite3 import Connection


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "support_agent.db"


def get_connection() -> Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_records (
                ticket_id TEXT PRIMARY KEY,
                approval_status TEXT NOT NULL,
                approval_id TEXT,
                approved_by TEXT,
                approval_notes TEXT,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS action_execution_records (
                idempotency_key TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL,
                approval_id TEXT NOT NULL,
                approved_by TEXT,
                action_type TEXT NOT NULL,
                write_action_executed INTEGER NOT NULL,
                duplicate_prevented INTEGER NOT NULL,
                side_effect TEXT NOT NULL,
                tool_type TEXT NOT NULL,
                execution_summary TEXT NOT NULL,
                raw_result_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()
