

import json
from pathlib import Path

from app.schemas import ApprovalRecord


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
APPROVALS_PATH = DATA_DIR / "approvals.json"


def _ensure_store_exists() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not APPROVALS_PATH.exists():
        APPROVALS_PATH.write_text("{}", encoding="utf-8")


def _load_raw_store() -> dict[str, dict]:
    _ensure_store_exists()
    raw_text = APPROVALS_PATH.read_text(encoding="utf-8").strip()

    if not raw_text:
        return {}

    data = json.loads(raw_text)
    if not isinstance(data, dict):
        raise ValueError("Approval store must contain a JSON object.")

    return data


def _save_raw_store(data: dict[str, dict]) -> None:
    _ensure_store_exists()
    APPROVALS_PATH.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def save_approval_record(record: ApprovalRecord) -> ApprovalRecord:
    data = _load_raw_store()
    data[record.ticket_id] = record.model_dump()
    _save_raw_store(data)
    return record


def get_approval_record(ticket_id: str) -> ApprovalRecord | None:
    data = _load_raw_store()
    record_data = data.get(ticket_id)

    if record_data is None:
        return None

    return ApprovalRecord(**record_data)


def clear_approval_store() -> None:
    """
    Test helper for clearing the local approval store.

    This is intentionally simple because the current project uses a local JSON file
    before introducing durable database-backed approval storage.
    """
    _save_raw_store({})