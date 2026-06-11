from __future__ import annotations

import json
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.graph import create_initial_state, refund_decision_graph
import app.nodes as nodes


PROJECT_DIR = Path(__file__).resolve().parents[1]
TEST_CASES_PATH = Path(__file__).resolve().with_name("test_cases.json")
PROHIBITED_RESPONSE_TERMS = (" issued ", " processed ", " executed ")


@contextmanager
def temporary_records_path() -> Iterator[Path]:
    original_path = nodes.DECISION_RECORDS_PATH
    with tempfile.TemporaryDirectory(prefix="refund-eval-") as temp_dir:
        records_path = Path(temp_dir) / "decision_records.json"
        records_path.write_text("[]\n", encoding="utf-8")
        nodes.DECISION_RECORDS_PATH = records_path
        try:
            yield records_path
        finally:
            nodes.DECISION_RECORDS_PATH = original_path


def load_test_cases() -> list[dict[str, Any]]:
    with TEST_CASES_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("eval test cases must be a JSON array")
    return payload


def assert_safe_response(final_response: str | None) -> None:
    response = f" {str(final_response or '').lower()} "
    for term in PROHIBITED_RESPONSE_TERMS:
        if term in response:
            raise AssertionError(
                f"final response claims a refund was already{term.strip()}: {final_response}"
            )


def run_case(test_case: dict[str, Any]) -> dict[str, Any]:
    initial_state = create_initial_state(
        request_id=str(test_case["request_id"]),
        customer_id=str(test_case["customer_id"]),
        user_message=str(test_case["user_message"]),
        debug=True,
        classifier_mode="mock",
    )
    result = refund_decision_graph.invoke(initial_state)

    assert result.get("refund_eligible") == test_case["expected_refund_eligible"], (
        f"refund_eligible mismatch: expected {test_case['expected_refund_eligible']!r}, "
        f"got {result.get('refund_eligible')!r}"
    )
    assert result.get("risk_level") == test_case["expected_risk_level"], (
        f"risk_level mismatch: expected {test_case['expected_risk_level']!r}, "
        f"got {result.get('risk_level')!r}"
    )
    assert result.get("needs_human_review") == test_case["expected_needs_human_review"], (
        f"needs_human_review mismatch: expected {test_case['expected_needs_human_review']!r}, "
        f"got {result.get('needs_human_review')!r}"
    )
    assert result.get("final_node") == test_case["expected_final_node"], (
        f"final_node mismatch: expected {test_case['expected_final_node']!r}, "
        f"got {result.get('final_node')!r}"
    )
    assert result.get("persistence_status") == "persisted", (
        f"expected persisted record, got {result.get('persistence_status')!r}"
    )
    assert_safe_response(result.get("final_response"))

    return {
        "name": test_case["name"],
        "status": "PASS",
        "final_node": result.get("final_node"),
        "refund_eligible": result.get("refund_eligible"),
        "risk_level": result.get("risk_level"),
        "needs_human_review": result.get("needs_human_review"),
        "workflow_path": result.get("workflow_path", []),
    }


def main() -> int:
    test_cases = load_test_cases()
    passed = 0
    failed = 0

    print("Refund decision agent eval")
    print(f"Project: {PROJECT_DIR}")
    print(f"Cases: {len(test_cases)}")

    with temporary_records_path():
        for test_case in test_cases:
            try:
                outcome = run_case(test_case)
                passed += 1
                print(
                    f"[PASS] {outcome['name']} -> "
                    f"final_node={outcome['final_node']}, "
                    f"refund_eligible={outcome['refund_eligible']}, "
                    f"risk_level={outcome['risk_level']}, "
                    f"needs_human_review={outcome['needs_human_review']}"
                )
            except Exception as error:
                failed += 1
                print(f"[FAIL] {test_case.get('name', test_case.get('request_id', 'unknown'))}: {error}")

    print(f"Summary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
