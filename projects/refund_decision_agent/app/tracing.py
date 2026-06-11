from __future__ import annotations

from typing import Any

from app.schemas import TraceEvent


def append_workflow_path(path: list[str], node_name: str) -> list[str]:
    cleaned_node_name = node_name.strip()
    if not cleaned_node_name:
        raise ValueError("node_name must not be blank")
    return [*path, cleaned_node_name]


def add_trace_event(
    trace_events: list[dict[str, Any]],
    node: str,
    event_type: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    cleaned_metadata = metadata or {}
    normalized_metadata = {key: cleaned_metadata[key] for key in sorted(cleaned_metadata)}
    trace_event = TraceEvent(
        node=node,
        event_type=event_type,
        message=message,
        metadata=normalized_metadata,
    )
    return [*trace_events, trace_event.model_dump()]
