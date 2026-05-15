

from app.tools import (
    get_technical_diagnostics,
    lookup_billing_record,
    preview_high_risk_action,
)


def test_lookup_billing_record_returns_read_only_evidence():
    result = lookup_billing_record(ticket_id="TOOL-001", customer_id="CUSTOMER-001")

    assert result.tool_name == "lookup_billing_record"
    assert result.status == "success"
    assert result.result["ticket_id"] == "TOOL-001"
    assert result.result["customer_id"] == "CUSTOMER-001"
    assert result.result["possible_duplicate_charge"] is True
    assert result.result["tool_type"] == "read_only"
    assert result.result["side_effect"] == "none"


def test_lookup_billing_record_uses_mock_customer_when_missing():
    result = lookup_billing_record(ticket_id="TOOL-002")

    assert result.result["customer_id"] == "mock_customer_unknown"
    assert result.result["tool_type"] == "read_only"
    assert result.result["side_effect"] == "none"


def test_get_technical_diagnostics_returns_read_only_checklist():
    result = get_technical_diagnostics(ticket_id="TOOL-003")

    assert result.tool_name == "get_technical_diagnostics"
    assert result.status == "success"
    assert result.result["ticket_id"] == "TOOL-003"
    assert result.result["tool_type"] == "read_only"
    assert result.result["side_effect"] == "none"
    assert "app_version" in result.result["requested_diagnostics"]
    assert "device_os" in result.result["requested_diagnostics"]
    assert "reproduction_steps" in result.result["requested_diagnostics"]


def test_preview_high_risk_action_is_preview_only_and_does_not_execute_write():
    result = preview_high_risk_action(
        ticket_id="TOOL-004",
        intent="high_risk_account_or_financial_action",
    )

    assert result.tool_name == "preview_high_risk_action"
    assert result.status == "success"
    assert result.result["ticket_id"] == "TOOL-004"
    assert result.result["intent"] == "high_risk_account_or_financial_action"
    assert result.result["tool_type"] == "preview_only"
    assert result.result["side_effect"] == "none"
    assert result.result["requires_human_approval"] is True
    assert result.result["write_action_executed"] is False


def test_preview_high_risk_action_uses_unknown_intent_fallback():
    result = preview_high_risk_action(ticket_id="TOOL-005", intent=None)

    assert result.result["intent"] == "unknown_high_risk_intent"
    assert result.result["requires_human_approval"] is True
    assert result.result["write_action_executed"] is False