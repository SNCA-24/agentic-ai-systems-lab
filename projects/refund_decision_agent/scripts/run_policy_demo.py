from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from app.policy_store import PolicyStore


QUERIES = [
    {
        "name": "duplicate charge policy retrieval",
        "query": "I was charged twice for the same invoice and want a refund.",
        "intent": "duplicate_charge_refund",
    },
    {
        "name": "post-cancellation billing retrieval",
        "query": "I was charged after cancellation and need the right policy.",
        "intent": "post_cancellation_charge_refund",
    },
    {
        "name": "conflicting evidence escalation retrieval",
        "query": "The evidence is conflicting and I need manual review guidance.",
        "intent": "unclear_refund_request",
    },
]


def main() -> int:
    store = PolicyStore()

    print("Refund decision agent policy demo")
    print(f"Project: {PROJECT_DIR}")
    print(f"Loaded policy sections: {len(store.sections)}")

    for item in QUERIES:
        documents = store.search(query=item["query"], intent=item["intent"], limit=3)
        print()
        print(
            json.dumps(
                {
                    "scenario": item["name"],
                    "query": item["query"],
                    "intent": item["intent"],
                    "results": [
                        {
                            "source": document.source,
                            "section_title": document.section_title,
                            "section_ref": document.section_ref,
                            "score": document.score,
                        }
                        for document in documents
                    ],
                },
                indent=2,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
