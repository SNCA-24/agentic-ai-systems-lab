

from langgraph.checkpoint.memory import MemorySaver


DEFAULT_THREAD_PREFIX = "support-ticket"


def create_memory_checkpointer() -> MemorySaver:
    """
    Create an in-memory LangGraph checkpointer for local durable-workflow experiments.

    This is the first step toward durable human-in-the-loop workflows. It is not
    database-backed persistence yet. It allows local thread_id-based checkpointing
    while we validate the graph behavior before moving to a persistent checkpointer.
    """
    return MemorySaver()


def build_thread_id(ticket_id: str, prefix: str = DEFAULT_THREAD_PREFIX) -> str:
    """
    Build a stable thread_id for LangGraph checkpointed runs.

    In production, this could be replaced with a stronger workflow/session ID.
    For this project, ticket_id is stable enough for local durable workflow tests.
    """
    return f"{prefix}:{ticket_id}"


def build_graph_config(thread_id: str) -> dict:
    """
    Build LangGraph config containing the checkpoint thread_id.

    LangGraph checkpointers use configurable.thread_id to associate multiple graph
    invocations with the same logical workflow thread.
    """
    return {
        "configurable": {
            "thread_id": thread_id,
        }
    }