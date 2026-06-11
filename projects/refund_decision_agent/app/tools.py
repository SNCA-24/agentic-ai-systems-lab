from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
CUSTOMERS_PATH = DATA_DIR / "mock_customers.json"
BILLING_RECORDS_PATH = DATA_DIR / "mock_billing_records.json"


@lru_cache(maxsize=1)
def _load_customers() -> list[dict[str, Any]]:
    with CUSTOMERS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _load_billing_records() -> list[dict[str, Any]]:
    with BILLING_RECORDS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _find_customer(customer_id: str) -> dict[str, Any] | None:
    for customer in _load_customers():
        if customer["customer_id"] == customer_id:
            return customer
    return None


def lookup_customer_profile(customer_id: str) -> dict[str, Any]:
    customer = _find_customer(customer_id)
    if customer is None:
        return {
            "customer_id": customer_id,
            "customer_found": False,
            "account_type": "unknown",
            "plan_name": None,
            "signup_date": None,
        }

    return {
        "customer_id": customer_id,
        "customer_found": True,
        "account_type": customer["account_type"],
        "plan_name": customer["plan_name"],
        "signup_date": customer["signup_date"],
    }


def lookup_subscription_status(customer_id: str) -> dict[str, Any]:
    customer = _find_customer(customer_id)
    if customer is None:
        return {
            "customer_id": customer_id,
            "customer_found": False,
            "subscription_status": "unknown",
        }

    return {
        "customer_id": customer_id,
        "customer_found": True,
        "subscription_status": customer["subscription_status"],
    }


def lookup_recent_charges(customer_id: str) -> dict[str, Any]:
    customer = _find_customer(customer_id)
    charges = [deepcopy(record) for record in _load_billing_records() if record["customer_id"] == customer_id]
    return {
        "customer_id": customer_id,
        "customer_found": customer is not None,
        "recent_charges": charges,
    }


def lookup_cancellation_timestamp(customer_id: str) -> dict[str, Any]:
    customer = _find_customer(customer_id)
    if customer is None:
        return {
            "customer_id": customer_id,
            "customer_found": False,
            "cancellation_timestamp": None,
        }

    return {
        "customer_id": customer_id,
        "customer_found": True,
        "cancellation_timestamp": customer["cancellation_timestamp"],
    }


def lookup_refund_history(customer_id: str) -> dict[str, Any]:
    customer = _find_customer(customer_id)
    if customer is None:
        return {
            "customer_id": customer_id,
            "customer_found": False,
            "refund_history": [],
        }

    return {
        "customer_id": customer_id,
        "customer_found": True,
        "refund_history": deepcopy(customer.get("refund_history", [])),
    }
