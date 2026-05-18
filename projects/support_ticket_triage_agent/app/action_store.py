import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
ACTION_EXECUTIONS_PATH = DATA_DIR / "action_executions.json"


def _ensure_store_exists() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ACTION_EXECUTIONS_PATH.exists():
        ACTION_EXECUTIONS_PATH.write_text("{}", encoding="utf-8")


def _load_raw_store() -> dict[str, dict[str, Any]]:
    _ensure_store_exists()
    raw_text = ACTION_EXECUTIONS_PATH.read_text(encoding="utf-8").strip()

    if not raw_text:
        return {}

    data = json.loads(raw_text)
    if not isinstance(data, dict):
        raise ValueError("Action execution store must contain a JSON object.")

    return data


def _save_raw_store(data: dict[str, dict[str, Any]]) -> None:
    _ensure_store_exists()
    ACTION_EXECUTIONS_PATH.write_text(
        json.dumps(data, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def build_idempotency_key(
    ticket_id: str,
    approval_id: str,
    action_type: str,
) -> str:
    return f"{ticket_id}:{approval_id}:{action_type}"


def get_action_execution(idempotency_key: str) -> dict[str, Any] | None:
    data = _load_raw_store()
    return data.get(idempotency_key)


def save_action_execution(
    idempotency_key: str,
    execution_record: dict[str, Any],
) -> dict[str, Any]:
    data = _load_raw_store()
    data[idempotency_key] = execution_record
    _save_raw_store(data)
    return execution_record


def clear_action_store() -> None:
    """
    Test helper for clearing the local action execution store.
    """
    _save_raw_store({})
