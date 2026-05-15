

from typing import Literal

from pydantic import BaseModel, Field


ToolStatus = Literal["success", "failed", "skipped"]


class ToolExecutionResult(BaseModel):
    tool_name: str
    status: ToolStatus
    result: dict = Field(default_factory=dict)


def lookup_billing_record(ticket_id: str, customer_id: str | None = None) -> ToolExecutionResult:
    """
    Simulated read-only billing lookup tool.

    This tool does not modify billing state. It returns deterministic mock evidence
    that can be stored in AgentState.tool_results.
    """
    return ToolExecutionResult(
        tool_name="lookup_billing_record",
        status="success",
        result={
            "ticket_id": ticket_id,
            "customer_id": customer_id or "mock_customer_unknown",
            "recent_charge_count": 2,
            "possible_duplicate_charge": True,
            "recommended_next_step": "Review billing ledger and refund policy before taking action.",
            "side_effect": "none",
            "tool_type": "read_only",
        },
    )


def get_technical_diagnostics(ticket_id: str) -> ToolExecutionResult:
    """
    Simulated read-only diagnostics helper for technical tickets.

    This tool returns a checklist of diagnostic evidence to collect. It does not
    inspect or modify any real production system.
    """
    return ToolExecutionResult(
        tool_name="get_technical_diagnostics",
        status="success",
        result={
            "ticket_id": ticket_id,
            "requested_diagnostics": [
                "app_version",
                "device_os",
                "error_timestamp",
                "reproduction_steps",
                "logs_or_screenshot",
            ],
            "recommended_next_step": "Collect diagnostics before escalating to engineering.",
            "side_effect": "none",
            "tool_type": "read_only",
        },
    )


def preview_high_risk_action(ticket_id: str, intent: str | None) -> ToolExecutionResult:
    """
    Simulated high-risk action preview tool.

    This is intentionally a preview, not an executor. It helps reviewers understand
    the requested action while preserving the rule that high-risk write actions
    must not execute before approval.
    """
    return ToolExecutionResult(
        tool_name="preview_high_risk_action",
        status="success",
        result={
            "ticket_id": ticket_id,
            "intent": intent or "unknown_high_risk_intent",
            "action_preview": "High-risk account, permission, security, or financial action requires human approval.",
            "requires_human_approval": True,
            "write_action_executed": False,
            "recommended_next_step": "Verify requester identity and obtain approval before any write action.",
            "side_effect": "none",
            "tool_type": "preview_only",
        },
    )