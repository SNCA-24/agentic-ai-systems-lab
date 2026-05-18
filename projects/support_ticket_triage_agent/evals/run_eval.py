import json
from pathlib import Path

from app.config import (
    APP_ENV,
    CLASSIFIER_MODE,
    LANGSMITH_PROJECT_NAME,
    LANGSMITH_RUN_TAG_PREFIX,
)
from app.graph import ticket_graph
from app.state import AgentState


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_CASES_PATH = PROJECT_ROOT / "evals" / "test_cases.json"


def run_single_eval(test_case: dict) -> dict:
    initial_state: AgentState = {
        "ticket_id": test_case["ticket_id"],
        "user_message": test_case["user_message"],
        "category": None,
        "intent": None,
        "risk_level": None,
        "needs_human_review": False,
        "confidence": None,
        "decision_summary": None,
        "approval_status": "not_required",
        "approval_id": None,
        "approval_notes": None,
        "approved_by": None,
        "workflow_path": [],
        "trace_events": [],
        "tool_results": [],
        "errors": [],
        "final_response": None,
    }

    config = {
        "run_name": "support_ticket_triage_eval_run",
        "tags": [
            LANGSMITH_RUN_TAG_PREFIX,
            "eval-run",
            f"classifier:{CLASSIFIER_MODE}",
            f"env:{APP_ENV}",
        ],
        "metadata": {
            "ticket_id": test_case["ticket_id"],
            "classifier_mode": CLASSIFIER_MODE,
            "run_source": "eval",
            "environment": APP_ENV,
            "langsmith_project": LANGSMITH_PROJECT_NAME,
            "expected_category": test_case["expected_category"],
            "expected_risk_level": test_case["expected_risk_level"],
            "expected_needs_human_review": test_case["expected_needs_human_review"],
            "expected_final_node": test_case.get("expected_final_node"),
        },
    }
    result = ticket_graph.invoke(initial_state, config=config)

    expected_final_node = test_case.get("expected_final_node")
    expected_approval_status = test_case.get(
        "expected_approval_status",
        "pending" if test_case["expected_needs_human_review"] else "not_required",
    )
    actual_final_node = result["workflow_path"][-1] if result.get("workflow_path") else None
    trace_events_count = len(result.get("trace_events", []))

    checks = {
        "category_correct": result["category"] == test_case["expected_category"],
        "risk_level_correct": result["risk_level"] == test_case["expected_risk_level"],
        "human_review_correct": (
            result["needs_human_review"] == test_case["expected_needs_human_review"]
        ),
        "approval_status_correct": result["approval_status"] == expected_approval_status,
        "trace_events_recorded": trace_events_count >= 3,
    }

    if expected_final_node is not None:
        checks["final_node_correct"] = actual_final_node == expected_final_node

    return {
        "ticket_id": test_case["ticket_id"],
        "passed": all(checks.values()),
        "checks": checks,
        "expected": {
            "category": test_case["expected_category"],
            "risk_level": test_case["expected_risk_level"],
            "needs_human_review": test_case["expected_needs_human_review"],
            "approval_status": expected_approval_status,
            "final_node": expected_final_node,
        },
        "actual": {
            "category": result["category"],
            "intent": result["intent"],
            "risk_level": result["risk_level"],
            "needs_human_review": result["needs_human_review"],
            "approval_status": result["approval_status"],
            "confidence": result["confidence"],
            "decision_summary": result["decision_summary"],
            "workflow_path": result.get("workflow_path", []),
            "trace_events_count": trace_events_count,
            "final_node": actual_final_node,
            "final_response": result["final_response"],
            "errors": result["errors"],
            "tool_results": result["tool_results"],
        },
    }


def run_all_evals() -> list[dict]:
    with TEST_CASES_PATH.open("r", encoding="utf-8") as file:
        test_cases = json.load(file)

    results = [run_single_eval(case) for case in test_cases]

    print(f"Classifier mode: {CLASSIFIER_MODE}")
    print(f"Environment: {APP_ENV}")
    print(f"LangSmith project: {LANGSMITH_PROJECT_NAME}")

    total = len(results)
    passed = sum(1 for item in results if item["passed"])

    print(f"\nPassed {passed}/{total} evals")

    for item in results:
        status = "PASS" if item["passed"] else "FAIL"
        print(f"\n[{status}] {item['ticket_id']}")
        print("Expected:", item["expected"])
        print("Actual:", item["actual"])
        print("Checks:", item["checks"])

    return results


if __name__ == "__main__":
    run_all_evals()