import json
from pathlib import Path

from app.tools import (
    lookup_cancellation_timestamp,
    lookup_customer_profile,
    lookup_recent_charges,
    lookup_refund_history,
    lookup_subscription_status,
)


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
CUSTOMERS_PATH = DATA_DIR / "mock_customers.json"
BILLING_RECORDS_PATH = DATA_DIR / "mock_billing_records.json"
DECISION_RECORDS_PATH = DATA_DIR / "decision_records.json"


def _load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_mock_customer_fixtures_cover_required_milestone_1_scenarios():
    customers = _load_json(CUSTOMERS_PATH)
    billing_records = _load_json(BILLING_RECORDS_PATH)
    assert isinstance(customers, list)

    customer_ids = [customer["customer_id"] for customer in customers]
    assert len(customer_ids) == len(set(customer_ids))

    billing_charge_ids = {record["charge_id"] for record in billing_records}
    for customer in customers:
        for refund in customer.get("refund_history", []):
            assert refund["charge_id"] in billing_charge_ids

    by_id = {customer["customer_id"]: customer for customer in customers}

    assert "cust_001" in by_id
    assert by_id["cust_001"]["account_type"] == "standard"

    assert "cust_002" in by_id
    assert by_id["cust_002"]["subscription_status"] == "cancelled"
    assert by_id["cust_002"]["cancellation_timestamp"]

    assert "cust_003" in by_id
    assert by_id["cust_003"]["account_type"] == "standard"

    assert "cust_004" in by_id
    assert by_id["cust_004"]["account_type"] == "enterprise"

    assert "cust_005" in by_id
    assert by_id["cust_005"]["account_type"] == "standard"

    assert "cust_missing" not in by_id


def test_mock_billing_records_cover_required_milestone_1_scenarios():
    records = _load_json(BILLING_RECORDS_PATH)
    assert isinstance(records, list)

    raw_customer_ids = [record["customer_id"] for record in records]
    assert {"cust_001", "cust_002", "cust_003", "cust_004", "cust_005"} <= set(raw_customer_ids)
    assert raw_customer_ids.count("cust_001") == 2
    assert raw_customer_ids.count("cust_002") == 1
    assert raw_customer_ids.count("cust_003") == 1
    assert raw_customer_ids.count("cust_004") == 1
    assert raw_customer_ids.count("cust_005") == 1
    assert "cust_missing" not in raw_customer_ids

    by_customer = {}
    for record in records:
        by_customer.setdefault(record["customer_id"], []).append(record)

    duplicate_records = by_customer["cust_001"]
    assert len(duplicate_records) >= 2
    assert sum(record.get("is_duplicate", False) for record in duplicate_records) >= 1

    cancelled_records = by_customer["cust_002"]
    assert any(record.get("charge_timing") == "post_cancellation" for record in cancelled_records)

    outside_window_records = by_customer["cust_003"]
    assert any(record.get("within_refund_window") is False for record in outside_window_records)

    enterprise_records = by_customer["cust_004"]
    assert any(record["amount"] >= 100 for record in enterprise_records)
    assert any(record.get("billing_period") == "annual" for record in enterprise_records)

    conflicting_records = by_customer["cust_005"]
    assert any(record.get("has_conflicting_evidence") is True for record in conflicting_records)

    assert "cust_missing" not in by_customer


def test_decision_records_fixture_starts_as_empty_array():
    records = _load_json(DECISION_RECORDS_PATH)
    assert records == []


def test_lookup_customer_profile_returns_fixture_backed_profile():
    profile = lookup_customer_profile("cust_004")

    assert profile == {
        "customer_id": "cust_004",
        "customer_found": True,
        "account_type": "enterprise",
        "plan_name": "Enterprise Annual",
        "signup_date": "2026-01-01T00:00:00Z",
    }


def test_lookup_subscription_status_returns_fixture_backed_status():
    status = lookup_subscription_status("cust_002")

    assert status == {
        "customer_id": "cust_002",
        "customer_found": True,
        "subscription_status": "cancelled",
    }


def test_lookup_recent_charges_returns_duplicate_charge_fixture():
    charges = lookup_recent_charges("cust_001")

    assert charges["customer_id"] == "cust_001"
    assert charges["customer_found"] is True
    assert len(charges["recent_charges"]) == 2
    assert any(charge["is_duplicate"] is True for charge in charges["recent_charges"])


def test_lookup_cancellation_timestamp_returns_fixture_value():
    cancellation = lookup_cancellation_timestamp("cust_002")

    assert cancellation == {
        "customer_id": "cust_002",
        "customer_found": True,
        "cancellation_timestamp": "2026-05-02T09:15:00Z",
    }


def test_lookup_refund_history_returns_safe_empty_history_for_known_customer():
    history = lookup_refund_history("cust_003")

    assert history == {
        "customer_id": "cust_003",
        "customer_found": True,
        "refund_history": [],
    }


def test_unknown_customer_returns_safe_defaults_from_tools():
    assert lookup_customer_profile("cust_missing") == {
        "customer_id": "cust_missing",
        "customer_found": False,
        "account_type": "unknown",
        "plan_name": None,
        "signup_date": None,
    }
    assert lookup_subscription_status("cust_missing") == {
        "customer_id": "cust_missing",
        "customer_found": False,
        "subscription_status": "unknown",
    }
    assert lookup_recent_charges("cust_missing") == {
        "customer_id": "cust_missing",
        "customer_found": False,
        "recent_charges": [],
    }
    assert lookup_cancellation_timestamp("cust_missing") == {
        "customer_id": "cust_missing",
        "customer_found": False,
        "cancellation_timestamp": None,
    }
    assert lookup_refund_history("cust_missing") == {
        "customer_id": "cust_missing",
        "customer_found": False,
        "refund_history": [],
    }


def test_lookup_recent_charges_customer_found_depends_on_customer_fixture_not_charge_presence():
    charges = lookup_recent_charges("cust_003")

    assert charges["customer_id"] == "cust_003"
    assert charges["customer_found"] is True
    assert len(charges["recent_charges"]) == 1
