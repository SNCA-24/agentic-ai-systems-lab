from __future__ import annotations

import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from app.graph import create_initial_state, refund_decision_graph
import app.nodes as nodes


SCENARIOS = [
    {
        "name": "duplicate charge refund",
        "request_id": "DEMO-001",
        "customer_id": "cust_001",
        "user_message": "I was charged twice for my subscription. Can I get one charge refunded?",
    },
    {
        "name": "charge after cancellation",
        "request_id": "DEMO-002",
        "customer_id": "cust_002",
        "user_message": "I cancelled yesterday but was charged today. Can I get a refund?",
    },
    {
        "name": "outside refund window",
        "request_id": "DEMO-003",
        "customer_id": "cust_003",
        "user_message": "I want a refund even though this charge is outside the refund window.",
    },
    {
        "name": "high-value enterprise refund",
        "request_id": "DEMO-004",
        "customer_id": "cust_004",
        "user_message": "Please review a refund for our enterprise annual subscription.",
    },
    {
        "name": "conflicting evidence",
        "request_id": "DEMO-005",
        "customer_id": "cust_005",
        "user_message": "The billing evidence is conflicting and I need help with this refund.",
    },
    {
        "name": "missing customer",
        "request_id": "DEMO-006",
        "customer_id": "cust_missing",
        "user_message": "I need a refund for a charge on my missing account.",
    },
]


@contextmanager
def temporary_records_path() -> Iterator[Path]:
    original_path = nodes.DECISION_RECORDS_PATH
    with tempfile.TemporaryDirectory(prefix="refund-demo-") as temp_dir:
        records_path = Path(temp_dir) / "decision_records.json"
        records_path.write_text("[]\n", encoding="utf-8")
        nodes.DECISION_RECORDS_PATH = records_path
        try:
            yield records_path
        finally:
            nodes.DECISION_RECORDS_PATH = original_path


def run_scenario(scenario: dict[str, str]) -> dict[str, object]:
    state = create_initial_state(
        request_id=scenario["request_id"],
        customer_id=scenario["customer_id"],
        user_message=scenario["user_message"],
        debug=True,
        classifier_mode="mock",
    )
    result = refund_decision_graph.invoke(state)
    return {
        "scenario": scenario["name"],
        "request_id": result["request_id"],
        "customer_id": result["customer_id"],
        "intent": result.get("intent"),
        "status": result.get("status"),
        "refund_eligible": result.get("refund_eligible"),
        "refund_amount": result.get("refund_amount"),
        "risk_level": result.get("risk_level"),
        "needs_human_review": result.get("needs_human_review"),
        "final_node": result.get("final_node"),
        "policy_basis": result.get("policy_basis", []),
        "decision_reason": result.get("decision_reason"),
        "final_response": result.get("final_response"),
        "workflow_path": result.get("workflow_path", []),
        "persistence_status": result.get("persistence_status"),
    }


def main() -> int:
    print("Refund decision agent demo")
    print(f"Project: {PROJECT_DIR}")
    print(f"Scenarios: {len(SCENARIOS)}")

    with temporary_records_path():
        for scenario in SCENARIOS:
            outcome = run_scenario(scenario)
            print()
            print(json.dumps(outcome, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
