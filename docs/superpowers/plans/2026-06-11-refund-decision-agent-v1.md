# Refund Decision Agent v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, policy-grounded refund decision workflow in `projects/refund_decision_agent/` with JSON-only persistence, local evals, pytest coverage, and a thin FastAPI API that runs without API keys by default.

**Architecture:** The graph stays linear through validation, mock classification, local policy retrieval, mock evidence lookup, deterministic decisioning, deterministic terminal routing, and append-only JSON persistence. All work stays inside `projects/refund_decision_agent/`, with `CLASSIFIER_MODE=mock` as the default and any live LLM path kept isolated and non-default.

**Tech Stack:** Python, LangGraph, FastAPI, Pydantic, python-dotenv, pytest, local JSON/Markdown fixtures, optional LangSmith config

---

## Repository Boundary

All implementation in this plan is restricted to:

- `projects/refund_decision_agent/`

Do not modify:

- `projects/support_ticket_triage_agent/`
- root `README.md`
- unrelated monorepo files

The only repo-level files already added for process are this plan and the approved design spec under `docs/superpowers/`.

## File Map

### Runtime code

- Modify: `projects/refund_decision_agent/app/config.py`
- Modify: `projects/refund_decision_agent/app/state.py`
- Modify: `projects/refund_decision_agent/app/schemas.py`
- Modify: `projects/refund_decision_agent/app/errors.py`
- Modify: `projects/refund_decision_agent/app/tracing.py`
- Modify: `projects/refund_decision_agent/app/policy_store.py`
- Modify: `projects/refund_decision_agent/app/tools.py`
- Modify: `projects/refund_decision_agent/app/decision_engine.py`
- Modify: `projects/refund_decision_agent/app/nodes.py`
- Modify: `projects/refund_decision_agent/app/graph.py`
- Modify: `projects/refund_decision_agent/app/api.py`

### Data and fixtures

- Modify: `projects/refund_decision_agent/data/policies/refund_policy.md`
- Modify: `projects/refund_decision_agent/data/policies/cancellation_policy.md`
- Modify: `projects/refund_decision_agent/data/policies/billing_policy.md`
- Modify: `projects/refund_decision_agent/data/mock_customers.json`
- Modify: `projects/refund_decision_agent/data/mock_billing_records.json`
- Create: `projects/refund_decision_agent/data/decision_records.json`

### Verification and demos

- Modify: `projects/refund_decision_agent/evals/test_cases.json`
- Modify: `projects/refund_decision_agent/evals/run_eval.py`
- Modify: `projects/refund_decision_agent/scripts/run_demo.py`
- Modify: `projects/refund_decision_agent/scripts/run_policy_demo.py`
- Modify: `projects/refund_decision_agent/scripts/seed_data.py`
- Modify: `projects/refund_decision_agent/tests/test_policy_store.py`
- Modify: `projects/refund_decision_agent/tests/test_refund_tools.py`
- Modify: `projects/refund_decision_agent/tests/test_decision_engine.py`
- Modify: `projects/refund_decision_agent/tests/test_graph_routing.py`
- Modify: `projects/refund_decision_agent/tests/test_safety.py`
- Modify: `projects/refund_decision_agent/tests/test_api.py`

### Project docs and setup

- Modify: `projects/refund_decision_agent/.env.example`
- Modify: `projects/refund_decision_agent/Makefile`
- Modify: `projects/refund_decision_agent/requirements.txt`
- Modify: `projects/refund_decision_agent/README.md`
- Modify: `projects/refund_decision_agent/docs/refund_decision_agent_prd.md`

## Milestone 1: Foundation, Config, And Fixtures

### Task 1: Define config, state, schemas, and error primitives

**Files:**
- Modify: `projects/refund_decision_agent/app/config.py`
- Modify: `projects/refund_decision_agent/app/state.py`
- Modify: `projects/refund_decision_agent/app/schemas.py`
- Modify: `projects/refund_decision_agent/app/errors.py`
- Test: `projects/refund_decision_agent/tests/test_api.py`
- Test: `projects/refund_decision_agent/tests/test_decision_engine.py`

- [ ] **Step 1: Write the failing schema and validation tests**

```python
from app.schemas import RefundDecisionRequest, RefundDecisionResponse
from pydantic import ValidationError


def test_refund_decision_request_requires_core_fields():
    request = RefundDecisionRequest(
        request_id="REQ-001",
        customer_id="cust_001",
        user_message="I was charged twice.",
    )
    assert request.request_id == "REQ-001"
    assert request.customer_id == "cust_001"


def test_refund_decision_request_rejects_blank_message():
    try:
        RefundDecisionRequest(
            request_id="REQ-002",
            customer_id="cust_001",
            user_message="   ",
        )
    except ValidationError as exc:
        assert "user_message" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for blank user_message")


def test_refund_decision_response_hides_debug_fields_by_default():
    response = RefundDecisionResponse(
        request_id="REQ-003",
        customer_id="cust_001",
        refund_eligible=True,
        refund_amount=29.0,
        risk_level="medium",
        needs_human_review=False,
        decision_reason="Duplicate charge detected.",
        policy_basis=["refund_policy.md#duplicate-charges"],
        evidence_summary="Two identical charges were found.",
        final_response="You appear eligible for a refund review.",
        status="eligible",
        workflow_path=["eligible_response_node"],
        trace_events=[],
        errors=[],
        debug=False,
    )
    dumped = response.model_dump()
    assert dumped["final_response"].startswith("You appear eligible")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest projects/refund_decision_agent/tests/test_api.py -q`
Expected: `ImportError`, `ValidationError` mismatch, or missing schema fields because the request/response models are incomplete.

- [ ] **Step 3: Write the minimal config, state, schema, and error code**

```python
# projects/refund_decision_agent/app/config.py
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

APP_ENV = os.getenv("APP_ENV", "local")
CLASSIFIER_MODE = os.getenv("CLASSIFIER_MODE", "mock")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "refund-decision-agent")

DATA_DIR = BASE_DIR / "data"
POLICY_DIR = DATA_DIR / "policies"
CUSTOMERS_PATH = DATA_DIR / "mock_customers.json"
BILLING_RECORDS_PATH = DATA_DIR / "mock_billing_records.json"
DECISION_RECORDS_PATH = DATA_DIR / "decision_records.json"
```

```python
# projects/refund_decision_agent/app/state.py
from typing import Literal, Optional
from typing_extensions import TypedDict


class RefundDecisionState(TypedDict):
    request_id: str
    customer_id: str
    user_message: str
    intent: Optional[str]
    category: Optional[str]
    risk_level: Optional[Literal["low", "medium", "high"]]
    retrieved_policy_docs: list[dict]
    billing_evidence: dict
    customer_context: dict
    refund_eligible: Optional[bool]
    refund_amount: Optional[float]
    needs_human_review: bool
    decision_reason: Optional[str]
    policy_basis: list[str]
    evidence_summary: Optional[str]
    workflow_path: list[str]
    trace_events: list[dict]
    errors: list[str]
    final_response: Optional[str]
    status: Optional[str]
    final_node: Optional[str]
```

```python
# projects/refund_decision_agent/app/schemas.py
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class TraceEvent(BaseModel):
    node: str
    event_type: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RefundDecisionRequest(BaseModel):
    request_id: str
    customer_id: str
    user_message: str
    debug: bool = False

    @field_validator("request_id", "customer_id", "user_message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Field must not be blank.")
        return value.strip()


class RefundIntentClassification(BaseModel):
    intent: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high"]


class RetrievedPolicyDocument(BaseModel):
    source: str
    section_title: str
    section_ref: str
    score: float
    content: str


class BillingLookupResult(BaseModel):
    customer_found: bool
    subscription_status: Optional[str] = None
    cancellation_timestamp: Optional[str] = None
    recent_charges: list[dict] = Field(default_factory=list)
    refund_history: list[dict] = Field(default_factory=list)
    conflict_flags: list[str] = Field(default_factory=list)


class RefundEligibilityDecision(BaseModel):
    refund_eligible: Optional[bool]
    refund_amount: Optional[float] = None
    risk_level: Literal["low", "medium", "high"]
    needs_human_review: bool
    decision_reason: str
    policy_basis: list[str] = Field(default_factory=list)
    evidence_summary: str
    status: Literal["eligible", "ineligible", "human_review", "escalated"]


class RefundDecisionResponse(BaseModel):
    request_id: str
    customer_id: str
    refund_eligible: Optional[bool]
    refund_amount: Optional[float] = None
    risk_level: Literal["low", "medium", "high"]
    needs_human_review: bool
    decision_reason: str
    policy_basis: list[str] = Field(default_factory=list)
    evidence_summary: str
    final_response: str
    status: str
    workflow_path: list[str] = Field(default_factory=list)
    trace_events: list[TraceEvent] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    debug: bool = False

    def public_dump(self) -> dict[str, Any]:
        data = self.model_dump()
        if not self.debug:
            data.pop("workflow_path", None)
            data.pop("trace_events", None)
            data.pop("errors", None)
            data.pop("debug", None)
        return data


class DecisionRecord(BaseModel):
    request_id: str
    customer_id: str
    refund_eligible: Optional[bool]
    refund_amount: Optional[float]
    risk_level: Literal["low", "medium", "high"]
    needs_human_review: bool
    final_node: str
    status: str
    decision_reason: str
    policy_basis: list[str]
    evidence_summary: str
    timestamp: datetime
```

```python
# projects/refund_decision_agent/app/errors.py
class RefundDecisionError(Exception):
    """Base error for refund decision workflow failures."""


class PersistenceError(RefundDecisionError):
    """Raised when decision record persistence fails."""
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest projects/refund_decision_agent/tests/test_api.py -q`
Expected: schema-focused tests pass.

- [ ] **Step 5: Commit**

```bash
git add projects/refund_decision_agent/app/config.py \
  projects/refund_decision_agent/app/state.py \
  projects/refund_decision_agent/app/schemas.py \
  projects/refund_decision_agent/app/errors.py \
  projects/refund_decision_agent/tests/test_api.py
git commit -m "feat: add refund agent core schemas and config"
```

### Task 2: Add synthetic policies, mock fixtures, and JSON decision record seed

**Files:**
- Modify: `projects/refund_decision_agent/data/policies/refund_policy.md`
- Modify: `projects/refund_decision_agent/data/policies/cancellation_policy.md`
- Modify: `projects/refund_decision_agent/data/policies/billing_policy.md`
- Modify: `projects/refund_decision_agent/data/mock_customers.json`
- Modify: `projects/refund_decision_agent/data/mock_billing_records.json`
- Create: `projects/refund_decision_agent/data/decision_records.json`
- Test: `projects/refund_decision_agent/tests/test_refund_tools.py`
- Test: `projects/refund_decision_agent/tests/test_policy_store.py`

- [ ] **Step 1: Write the failing fixture and policy tests**

```python
from pathlib import Path
import json


def test_policy_files_cover_required_refund_scenarios():
    refund_policy = Path("projects/refund_decision_agent/data/policies/refund_policy.md").read_text()
    cancellation_policy = Path("projects/refund_decision_agent/data/policies/cancellation_policy.md").read_text()
    billing_policy = Path("projects/refund_decision_agent/data/policies/billing_policy.md").read_text()

    combined = "\n".join([refund_policy, cancellation_policy, billing_policy]).lower()
    assert "duplicate charge" in combined
    assert "post-cancellation" in combined or "after cancellation" in combined
    assert "refund window" in combined
    assert "enterprise" in combined
    assert "conflicting evidence" in combined or "unclear evidence" in combined


def test_decision_records_seed_is_json_array():
    data = json.loads(Path("projects/refund_decision_agent/data/decision_records.json").read_text())
    assert isinstance(data, list)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest projects/refund_decision_agent/tests/test_policy_store.py projects/refund_decision_agent/tests/test_refund_tools.py -q`
Expected: missing file content or missing seed file failures.

- [ ] **Step 3: Write the minimal fixture and policy data**

```md
# projects/refund_decision_agent/data/policies/refund_policy.md
# Refund Policy

## Duplicate Charges

Customers are eligible for a refund when the demo billing record confirms duplicate charges for the same plan and billing period.

## Refund Window

Standard self-serve refund requests must be made within 30 days of the charge date unless another policy section overrides this rule.

## High-Value Review

Refund requests above $100.00 require human review before any external action.

## Ambiguous Or Conflicting Evidence

If the available billing evidence is unclear, incomplete, or conflicting, the system must not auto-approve the request and must escalate for manual review.
```

```md
# projects/refund_decision_agent/data/policies/cancellation_policy.md
# Cancellation Policy

## Charges After Cancellation

If a customer was charged after a confirmed cancellation timestamp, the post-cancellation charge is eligible for refund review.

## Enterprise Accounts

Enterprise refund requests always require human review, even when the policy basis supports eligibility.
```

```md
# projects/refund_decision_agent/data/policies/billing_policy.md
# Billing Policy

## Duplicate Charge Detection

Matching amounts with the same billing period may be treated as duplicate charges when the mock record marks one charge as unintended.

## Missing Evidence

If customer or charge records cannot be found, the workflow must escalate instead of approving a refund.

## Conflicting Evidence

If subscription status, cancellation timing, or charge history disagree, the workflow must route the case to human review or escalation.
```

```json
// projects/refund_decision_agent/data/mock_customers.json
[
  {
    "customer_id": "cust_001",
    "name": "Casey Duplicate",
    "account_type": "standard",
    "subscription_status": "active",
    "refund_window_days": 30
  },
  {
    "customer_id": "cust_002",
    "name": "Robin Cancelled",
    "account_type": "standard",
    "subscription_status": "cancelled",
    "cancellation_timestamp": "2026-05-10T09:00:00Z",
    "refund_window_days": 30
  },
  {
    "customer_id": "cust_003",
    "name": "Taylor Late",
    "account_type": "standard",
    "subscription_status": "active",
    "refund_window_days": 30
  },
  {
    "customer_id": "cust_004",
    "name": "Northwind Enterprise",
    "account_type": "enterprise",
    "subscription_status": "active",
    "refund_window_days": 30
  },
  {
    "customer_id": "cust_005",
    "name": "Morgan Conflict",
    "account_type": "standard",
    "subscription_status": "cancelled",
    "cancellation_timestamp": "2026-05-12T12:00:00Z",
    "refund_window_days": 30
  }
]
```

```json
// projects/refund_decision_agent/data/mock_billing_records.json
[
  {
    "customer_id": "cust_001",
    "recent_charges": [
      {"charge_id": "ch_001", "amount": 29.0, "timestamp": "2026-05-01T00:00:00Z", "billing_period": "2026-05", "status": "posted"},
      {"charge_id": "ch_002", "amount": 29.0, "timestamp": "2026-05-01T00:05:00Z", "billing_period": "2026-05", "status": "posted", "duplicate_of": "ch_001"}
    ],
    "refund_history": []
  },
  {
    "customer_id": "cust_002",
    "recent_charges": [
      {"charge_id": "ch_003", "amount": 49.0, "timestamp": "2026-05-11T10:00:00Z", "billing_period": "2026-05", "status": "posted"}
    ],
    "refund_history": []
  },
  {
    "customer_id": "cust_003",
    "recent_charges": [
      {"charge_id": "ch_004", "amount": 19.0, "timestamp": "2026-03-01T10:00:00Z", "billing_period": "2026-03", "status": "posted"}
    ],
    "refund_history": []
  },
  {
    "customer_id": "cust_004",
    "recent_charges": [
      {"charge_id": "ch_005", "amount": 2000.0, "timestamp": "2026-05-15T10:00:00Z", "billing_period": "2026-annual", "status": "posted"}
    ],
    "refund_history": []
  },
  {
    "customer_id": "cust_005",
    "recent_charges": [
      {"charge_id": "ch_006", "amount": 59.0, "timestamp": "2026-05-11T10:00:00Z", "billing_period": "2026-05", "status": "posted"},
      {"charge_id": "ch_007", "amount": 59.0, "timestamp": "2026-05-13T10:00:00Z", "billing_period": "2026-05", "status": "reversed"}
    ],
    "refund_history": [{"charge_id": "ch_006", "status": "pending_investigation"}],
    "conflict_flags": ["charge_status_mismatch"]
  }
]
```

```json
// projects/refund_decision_agent/data/decision_records.json
[]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest projects/refund_decision_agent/tests/test_policy_store.py projects/refund_decision_agent/tests/test_refund_tools.py -q`
Expected: fixture presence tests pass.

- [ ] **Step 5: Commit**

```bash
git add projects/refund_decision_agent/data/policies/*.md \
  projects/refund_decision_agent/data/mock_customers.json \
  projects/refund_decision_agent/data/mock_billing_records.json \
  projects/refund_decision_agent/data/decision_records.json \
  projects/refund_decision_agent/tests/test_policy_store.py \
  projects/refund_decision_agent/tests/test_refund_tools.py
git commit -m "feat: add refund policy fixtures and mock billing data"
```

## Milestone 2: Retrieval, Tools, Tracing, And Deterministic Decisioning

### Task 3: Implement tracing helpers and policy retrieval

**Files:**
- Modify: `projects/refund_decision_agent/app/tracing.py`
- Modify: `projects/refund_decision_agent/app/policy_store.py`
- Test: `projects/refund_decision_agent/tests/test_policy_store.py`

- [ ] **Step 1: Write the failing retrieval tests**

```python
from app.policy_store import PolicyStore


def test_policy_store_returns_duplicate_charge_section_for_duplicate_request():
    store = PolicyStore()
    docs = store.search("I was charged twice for my subscription", intent="duplicate_charge_refund")
    assert docs
    assert any("duplicate" in doc.section_title.lower() or "duplicate" in doc.content.lower() for doc in docs)


def test_policy_store_returns_missing_evidence_guidance_for_unknown_customer():
    store = PolicyStore()
    docs = store.search("We cannot find this customer", intent="unclear_refund_request")
    assert any("missing evidence" in doc.content.lower() for doc in docs)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest projects/refund_decision_agent/tests/test_policy_store.py -q`
Expected: `PolicyStore` missing or retrieval assertions fail.

- [ ] **Step 3: Write minimal tracing and retrieval code**

```python
# projects/refund_decision_agent/app/tracing.py
from datetime import datetime, timezone
from typing import Any


def append_workflow_path(path: list[str], node_name: str) -> list[str]:
    return path + [node_name]


def add_trace_event(
    trace_events: list[dict],
    node: str,
    event_type: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> list[dict]:
    return trace_events + [
        {
            "node": node,
            "event_type": event_type,
            "message": message,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ]
```

```python
# projects/refund_decision_agent/app/policy_store.py
from dataclasses import dataclass
from pathlib import Path
import re

from app.config import POLICY_DIR
from app.schemas import RetrievedPolicyDocument


@dataclass
class PolicySection:
    source: str
    section_title: str
    section_ref: str
    content: str


class PolicyStore:
    def __init__(self, policy_dir: Path | None = None) -> None:
        self.policy_dir = policy_dir or POLICY_DIR
        self.sections = self._load_sections()

    def _load_sections(self) -> list[PolicySection]:
        sections: list[PolicySection] = []
        for path in sorted(self.policy_dir.glob("*.md")):
            heading = None
            body: list[str] = []
            for line in path.read_text().splitlines():
                if line.startswith("## "):
                    if heading and body:
                        sections.append(
                            PolicySection(
                                source=path.name,
                                section_title=heading,
                                section_ref=f"{path.name}#{heading.lower().replace(' ', '-')}",
                                content="\n".join(body).strip(),
                            )
                        )
                    heading = line.replace("## ", "").strip()
                    body = []
                elif heading:
                    body.append(line)
            if heading and body:
                sections.append(
                    PolicySection(
                        source=path.name,
                        section_title=heading,
                        section_ref=f"{path.name}#{heading.lower().replace(' ', '-')}",
                        content="\n".join(body).strip(),
                    )
                )
        return sections

    def search(self, query: str, intent: str | None = None, limit: int = 3) -> list[RetrievedPolicyDocument]:
        terms = set(re.findall(r"[a-z0-9]+", f"{query} {intent or ''}".lower()))
        scored: list[tuple[int, PolicySection]] = []
        for section in self.sections:
            haystack = f"{section.section_title} {section.content}".lower()
            score = sum(1 for term in terms if term in haystack)
            if score:
                scored.append((score, section))
        scored.sort(key=lambda item: (-item[0], item[1].source, item[1].section_title))
        return [
            RetrievedPolicyDocument(
                source=section.source,
                section_title=section.section_title,
                section_ref=section.section_ref,
                score=float(score),
                content=section.content,
            )
            for score, section in scored[:limit]
        ]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest projects/refund_decision_agent/tests/test_policy_store.py -q`
Expected: retrieval tests pass.

- [ ] **Step 5: Commit**

```bash
git add projects/refund_decision_agent/app/tracing.py \
  projects/refund_decision_agent/app/policy_store.py \
  projects/refund_decision_agent/tests/test_policy_store.py
git commit -m "feat: add local policy retrieval and tracing helpers"
```

### Task 4: Implement read-only mock tools and deterministic decision rules

**Files:**
- Modify: `projects/refund_decision_agent/app/tools.py`
- Modify: `projects/refund_decision_agent/app/decision_engine.py`
- Test: `projects/refund_decision_agent/tests/test_refund_tools.py`
- Test: `projects/refund_decision_agent/tests/test_decision_engine.py`

- [ ] **Step 1: Write the failing tools and decision tests**

```python
from app.decision_engine import HIGH_VALUE_REFUND_THRESHOLD, decide_refund_eligibility
from app.tools import (
    lookup_customer_profile,
    lookup_recent_charges,
    lookup_subscription_status,
)


def test_lookup_customer_profile_returns_safe_default_for_unknown_customer():
    result = lookup_customer_profile("cust_missing")
    assert result["customer_found"] is False
    assert result["customer_id"] == "cust_missing"


def test_lookup_recent_charges_returns_duplicate_charge_fixture():
    charges = lookup_recent_charges("cust_001")
    assert len(charges) == 2
    assert any(charge.get("duplicate_of") for charge in charges)


def test_decision_engine_marks_high_value_enterprise_as_human_review():
    decision = decide_refund_eligibility(
        customer_context={"account_type": "enterprise"},
        billing_evidence={"customer_found": True, "recent_charges": [{"amount": 2000.0}]},
        retrieved_policy_docs=[{"section_ref": "refund_policy.md#high-value-review"}],
        intent="enterprise_refund_request",
        user_message="Please refund our annual enterprise subscription.",
    )
    assert HIGH_VALUE_REFUND_THRESHOLD == 100.0
    assert decision.needs_human_review is True
    assert decision.risk_level == "high"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest projects/refund_decision_agent/tests/test_refund_tools.py projects/refund_decision_agent/tests/test_decision_engine.py -q`
Expected: missing functions or incorrect decision behavior.

- [ ] **Step 3: Write minimal tools and decision code**

```python
# projects/refund_decision_agent/app/tools.py
import json

from app.config import BILLING_RECORDS_PATH, CUSTOMERS_PATH


def _load_json(path):
    return json.loads(path.read_text())


def _customer_map() -> dict[str, dict]:
    return {item["customer_id"]: item for item in _load_json(CUSTOMERS_PATH)}


def _billing_map() -> dict[str, dict]:
    return {item["customer_id"]: item for item in _load_json(BILLING_RECORDS_PATH)}


def lookup_customer_profile(customer_id: str) -> dict:
    customer = _customer_map().get(customer_id)
    if not customer:
        return {"customer_found": False, "customer_id": customer_id}
    return {"customer_found": True, **customer}


def lookup_subscription_status(customer_id: str) -> dict:
    customer = lookup_customer_profile(customer_id)
    return {"customer_found": customer["customer_found"], "subscription_status": customer.get("subscription_status")}


def lookup_recent_charges(customer_id: str) -> list[dict]:
    return _billing_map().get(customer_id, {}).get("recent_charges", [])


def lookup_billing_record(customer_id: str) -> dict:
    return _billing_map().get(customer_id, {})


def lookup_cancellation_timestamp(customer_id: str) -> dict:
    customer = lookup_customer_profile(customer_id)
    return {"customer_found": customer["customer_found"], "cancellation_timestamp": customer.get("cancellation_timestamp")}


def lookup_refund_history(customer_id: str) -> list[dict]:
    return _billing_map().get(customer_id, {}).get("refund_history", [])
```

```python
# projects/refund_decision_agent/app/decision_engine.py
from datetime import datetime, timezone

from app.schemas import RefundEligibilityDecision

HIGH_VALUE_REFUND_THRESHOLD = 100.0
REFUND_WINDOW_DAYS = 30


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def decide_refund_eligibility(
    customer_context: dict,
    billing_evidence: dict,
    retrieved_policy_docs: list[dict],
    intent: str | None,
    user_message: str,
) -> RefundEligibilityDecision:
    if not billing_evidence.get("customer_found"):
        return RefundEligibilityDecision(
            refund_eligible=None,
            refund_amount=None,
            risk_level="high",
            needs_human_review=True,
            decision_reason="Customer record is missing from the mock data.",
            policy_basis=["billing_policy.md#missing-evidence"],
            evidence_summary="No customer profile was found for the provided customer_id.",
            status="escalated",
        )

    conflict_flags = billing_evidence.get("conflict_flags", [])
    if conflict_flags:
        return RefundEligibilityDecision(
            refund_eligible=None,
            refund_amount=None,
            risk_level="high",
            needs_human_review=True,
            decision_reason="The billing evidence is conflicting and requires manual review.",
            policy_basis=["billing_policy.md#conflicting-evidence"],
            evidence_summary=f"Conflict flags: {', '.join(conflict_flags)}",
            status="human_review",
        )

    charges = billing_evidence.get("recent_charges", [])
    duplicate_charge = next((charge for charge in charges if charge.get("duplicate_of")), None)
    if duplicate_charge:
        return RefundEligibilityDecision(
            refund_eligible=True,
            refund_amount=float(duplicate_charge["amount"]),
            risk_level="medium",
            needs_human_review=False,
            decision_reason="A duplicate charge is present in the mock billing data.",
            policy_basis=["refund_policy.md#duplicate-charges"],
            evidence_summary="Two matching charges were found in the same billing period.",
            status="eligible",
        )

    cancellation_ts = _parse_timestamp(customer_context.get("cancellation_timestamp"))
    post_cancel_charge = next(
        (
            charge
            for charge in charges
            if cancellation_ts and _parse_timestamp(charge.get("timestamp")) and _parse_timestamp(charge.get("timestamp")) > cancellation_ts
        ),
        None,
    )
    if post_cancel_charge:
        return RefundEligibilityDecision(
            refund_eligible=True,
            refund_amount=float(post_cancel_charge["amount"]),
            risk_level="medium",
            needs_human_review=False,
            decision_reason="The charge happened after the recorded cancellation timestamp.",
            policy_basis=["cancellation_policy.md#charges-after-cancellation"],
            evidence_summary="A posted charge was found after cancellation.",
            status="eligible",
        )

    first_charge = charges[0] if charges else None
    if first_charge:
        charge_ts = _parse_timestamp(first_charge.get("timestamp"))
        if charge_ts and (datetime.now(timezone.utc) - charge_ts).days > REFUND_WINDOW_DAYS:
            return RefundEligibilityDecision(
                refund_eligible=False,
                refund_amount=None,
                risk_level="low",
                needs_human_review=False,
                decision_reason="The request is outside the synthetic refund window.",
                policy_basis=["refund_policy.md#refund-window"],
                evidence_summary="The most relevant charge is older than 30 days.",
                status="ineligible",
            )

    amount = float(first_charge["amount"]) if first_charge else None
    enterprise = customer_context.get("account_type") == "enterprise"
    if amount is not None and (amount > HIGH_VALUE_REFUND_THRESHOLD or enterprise):
        return RefundEligibilityDecision(
            refund_eligible=True,
            refund_amount=amount,
            risk_level="high",
            needs_human_review=True,
            decision_reason="The request meets policy eligibility but requires human review.",
            policy_basis=["refund_policy.md#high-value-review", "cancellation_policy.md#enterprise-accounts"],
            evidence_summary="High refund amount or enterprise account requires review.",
            status="human_review",
        )

    return RefundEligibilityDecision(
        refund_eligible=None,
        refund_amount=None,
        risk_level="high",
        needs_human_review=True,
        decision_reason="The available mock evidence does not support an automatic decision.",
        policy_basis=["refund_policy.md#ambiguous-or-conflicting-evidence"],
        evidence_summary="The workflow could not match the request to a supported deterministic scenario.",
        status="escalated",
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest projects/refund_decision_agent/tests/test_refund_tools.py projects/refund_decision_agent/tests/test_decision_engine.py -q`
Expected: tools and decision rule tests pass.

- [ ] **Step 5: Commit**

```bash
git add projects/refund_decision_agent/app/tools.py \
  projects/refund_decision_agent/app/decision_engine.py \
  projects/refund_decision_agent/tests/test_refund_tools.py \
  projects/refund_decision_agent/tests/test_decision_engine.py
git commit -m "feat: add refund evidence tools and deterministic decision rules"
```

## Milestone 3: Graph Nodes, Routing, And JSON Persistence

### Task 5: Implement graph nodes including terminal-node persistence coverage

**Files:**
- Modify: `projects/refund_decision_agent/app/nodes.py`
- Test: `projects/refund_decision_agent/tests/test_graph_routing.py`
- Test: `projects/refund_decision_agent/tests/test_safety.py`

- [ ] **Step 1: Write the failing graph-node tests**

```python
from app.graph import refund_decision_graph


def test_duplicate_charge_routes_to_eligible_and_persists_record():
    result = refund_decision_graph.invoke(
        {
            "request_id": "REQ-100",
            "customer_id": "cust_001",
            "user_message": "I was charged twice for my subscription.",
            "intent": None,
            "category": None,
            "risk_level": None,
            "retrieved_policy_docs": [],
            "billing_evidence": {},
            "customer_context": {},
            "refund_eligible": None,
            "refund_amount": None,
            "needs_human_review": False,
            "decision_reason": None,
            "policy_basis": [],
            "evidence_summary": None,
            "workflow_path": [],
            "trace_events": [],
            "errors": [],
            "final_response": None,
            "status": None,
            "final_node": None,
        }
    )
    assert result["final_node"] == "eligible_response_node"
    assert result["workflow_path"][-1] == "persist_decision_node"


def test_validation_failure_still_reaches_persist_decision_node():
    result = refund_decision_graph.invoke(
        {
            "request_id": "REQ-101",
            "customer_id": "cust_missing",
            "user_message": "   ",
            "intent": None,
            "category": None,
            "risk_level": None,
            "retrieved_policy_docs": [],
            "billing_evidence": {},
            "customer_context": {},
            "refund_eligible": None,
            "refund_amount": None,
            "needs_human_review": False,
            "decision_reason": None,
            "policy_basis": [],
            "evidence_summary": None,
            "workflow_path": [],
            "trace_events": [],
            "errors": [],
            "final_response": None,
            "status": None,
            "final_node": None,
        }
    )
    assert result["final_node"] == "escalation_response_node"
    assert "persist_decision_node" in result["workflow_path"]
    assert result["errors"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest projects/refund_decision_agent/tests/test_graph_routing.py projects/refund_decision_agent/tests/test_safety.py -q`
Expected: graph import failure or missing node/routing behavior.

- [ ] **Step 3: Write minimal node implementation**

```python
# projects/refund_decision_agent/app/nodes.py
import json
from datetime import datetime, timezone

from app.config import CLASSIFIER_MODE, DECISION_RECORDS_PATH
from app.decision_engine import decide_refund_eligibility
from app.policy_store import PolicyStore
from app.tools import (
    lookup_billing_record,
    lookup_cancellation_timestamp,
    lookup_customer_profile,
    lookup_recent_charges,
    lookup_refund_history,
    lookup_subscription_status,
)
from app.tracing import add_trace_event, append_workflow_path


def validate_input_node(state):
    path = append_workflow_path(state["workflow_path"], "validate_input_node")
    message = state["user_message"].strip()
    if not state["request_id"] or not state["customer_id"] or not message:
        return {
            "workflow_path": path,
            "trace_events": add_trace_event(state["trace_events"], "validate_input_node", "validation_failed", "Refund request validation failed."),
            "errors": state["errors"] + ["Missing required refund request fields."],
            "status": "escalated",
        }
    return {
        "workflow_path": path,
        "trace_events": add_trace_event(state["trace_events"], "validate_input_node", "validation_passed", "Refund request validation passed."),
    }


def classify_refund_request_node(state):
    path = append_workflow_path(state["workflow_path"], "classify_refund_request_node")
    message = state["user_message"].lower()
    if "charged twice" in message or "duplicate" in message:
        intent = "duplicate_charge_refund"
        category = "refund"
        risk_level = "medium"
    elif "cancel" in message and "charged" in message:
        intent = "post_cancellation_charge_refund"
        category = "refund"
        risk_level = "medium"
    elif "enterprise" in message or "$2,000" in message or "annual subscription" in message:
        intent = "enterprise_refund_request"
        category = "refund"
        risk_level = "high"
    elif "refund" in message:
        intent = "general_refund_request"
        category = "refund"
        risk_level = "medium"
    else:
        intent = "unclear_refund_request"
        category = "billing"
        risk_level = "high"
    return {
        "workflow_path": path,
        "trace_events": add_trace_event(
            state["trace_events"],
            "classify_refund_request_node",
            "classification_completed",
            "Mock refund classification completed.",
            {"intent": intent, "classifier_mode": CLASSIFIER_MODE},
        ),
        "intent": intent,
        "category": category,
        "risk_level": risk_level,
    }


def retrieve_policy_context_node(state):
    path = append_workflow_path(state["workflow_path"], "retrieve_policy_context_node")
    store = PolicyStore()
    docs = [doc.model_dump() for doc in store.search(state["user_message"], intent=state.get("intent"))]
    return {
        "workflow_path": path,
        "trace_events": add_trace_event(state["trace_events"], "retrieve_policy_context_node", "policy_retrieval_completed", "Policy retrieval completed.", {"documents_found": len(docs)}),
        "retrieved_policy_docs": docs,
    }


def lookup_billing_evidence_node(state):
    path = append_workflow_path(state["workflow_path"], "lookup_billing_evidence_node")
    customer = lookup_customer_profile(state["customer_id"])
    billing_record = lookup_billing_record(state["customer_id"])
    subscription = lookup_subscription_status(state["customer_id"])
    cancellation = lookup_cancellation_timestamp(state["customer_id"])
    charges = lookup_recent_charges(state["customer_id"])
    refund_history = lookup_refund_history(state["customer_id"])
    billing = {
        "customer_found": customer.get("customer_found", False),
        "subscription_status": subscription.get("subscription_status"),
        "cancellation_timestamp": cancellation.get("cancellation_timestamp"),
        "recent_charges": charges,
        "refund_history": refund_history,
        "conflict_flags": billing_record.get("conflict_flags", []),
    }
    return {
        "workflow_path": path,
        "trace_events": add_trace_event(state["trace_events"], "lookup_billing_evidence_node", "billing_lookup_completed", "Mock billing lookup completed.", {"customer_found": billing["customer_found"], "charges_found": len(charges)}),
        "customer_context": customer,
        "billing_evidence": billing,
    }


def decide_refund_eligibility_node(state):
    path = append_workflow_path(state["workflow_path"], "decide_refund_eligibility_node")
    decision = decide_refund_eligibility(
        customer_context=state["customer_context"],
        billing_evidence=state["billing_evidence"],
        retrieved_policy_docs=state["retrieved_policy_docs"],
        intent=state.get("intent"),
        user_message=state["user_message"],
    )
    return {
        "workflow_path": path,
        "trace_events": add_trace_event(state["trace_events"], "decide_refund_eligibility_node", "decision_completed", "Deterministic refund decision completed.", {"status": decision.status}),
        "refund_eligible": decision.refund_eligible,
        "refund_amount": decision.refund_amount,
        "risk_level": decision.risk_level,
        "needs_human_review": decision.needs_human_review,
        "decision_reason": decision.decision_reason,
        "policy_basis": decision.policy_basis,
        "evidence_summary": decision.evidence_summary,
        "status": decision.status,
    }


def eligible_response_node(state):
    path = append_workflow_path(state["workflow_path"], "eligible_response_node")
    return {
        "workflow_path": path,
        "trace_events": add_trace_event(state["trace_events"], "eligible_response_node", "response_created", "Eligible response prepared."),
        "final_node": "eligible_response_node",
        "final_response": "You appear eligible for a refund review based on the demo policy and billing evidence. This workflow does not issue refunds automatically.",
    }


def ineligible_response_node(state):
    path = append_workflow_path(state["workflow_path"], "ineligible_response_node")
    return {
        "workflow_path": path,
        "trace_events": add_trace_event(state["trace_events"], "ineligible_response_node", "response_created", "Ineligible response prepared."),
        "final_node": "ineligible_response_node",
        "final_response": "Based on the demo policy and available billing evidence, this request does not appear eligible for a refund.",
    }


def human_review_required_node(state):
    path = append_workflow_path(state["workflow_path"], "human_review_required_node")
    return {
        "workflow_path": path,
        "trace_events": add_trace_event(state["trace_events"], "human_review_required_node", "response_created", "Human review response prepared."),
        "final_node": "human_review_required_node",
        "final_response": "This request needs manual review because it is high-value, enterprise-related, or otherwise risky under the demo policy.",
    }


def escalation_response_node(state):
    path = append_workflow_path(state["workflow_path"], "escalation_response_node")
    return {
        "workflow_path": path,
        "trace_events": add_trace_event(state["trace_events"], "escalation_response_node", "response_created", "Escalation response prepared."),
        "final_node": "escalation_response_node",
        "final_response": "The available demo evidence is incomplete or conflicting, so this request needs follow-up review.",
    }


def persist_decision_node(state):
    path = append_workflow_path(state["workflow_path"], "persist_decision_node")
    record = {
        "request_id": state["request_id"],
        "customer_id": state["customer_id"],
        "refund_eligible": state["refund_eligible"],
        "refund_amount": state["refund_amount"],
        "risk_level": state["risk_level"],
        "needs_human_review": state["needs_human_review"],
        "final_node": state["final_node"] or "unknown",
        "status": state["status"] or "escalated",
        "decision_reason": state["decision_reason"] or "",
        "policy_basis": state["policy_basis"],
        "evidence_summary": state["evidence_summary"] or "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        existing = json.loads(DECISION_RECORDS_PATH.read_text())
        existing.append(record)
        DECISION_RECORDS_PATH.write_text(json.dumps(existing, indent=2))
        return {
            "workflow_path": path,
            "trace_events": add_trace_event(state["trace_events"], "persist_decision_node", "persistence_succeeded", "Decision record persisted.", {"final_node": record["final_node"]}),
        }
    except Exception as exc:
        return {
            "workflow_path": path,
            "trace_events": add_trace_event(state["trace_events"], "persist_decision_node", "persistence_failed", "Decision persistence failed.", {"error": type(exc).__name__}),
            "errors": state["errors"] + [f"Decision persistence failed: {exc}"],
        }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest projects/refund_decision_agent/tests/test_graph_routing.py projects/refund_decision_agent/tests/test_safety.py -q`
Expected: routing and safety tests pass for terminal nodes and persistence coverage.

- [ ] **Step 5: Commit**

```bash
git add projects/refund_decision_agent/app/nodes.py \
  projects/refund_decision_agent/tests/test_graph_routing.py \
  projects/refund_decision_agent/tests/test_safety.py \
  projects/refund_decision_agent/data/decision_records.json
git commit -m "feat: add refund workflow nodes and json persistence"
```

### Task 6: Wire the LangGraph workflow with deterministic routing

**Files:**
- Modify: `projects/refund_decision_agent/app/graph.py`
- Test: `projects/refund_decision_agent/tests/test_graph_routing.py`

- [ ] **Step 1: Write the failing graph wiring tests**

```python
from app.graph import route_after_validation, route_after_decision


def test_route_after_validation_sends_errors_to_escalation():
    route = route_after_validation({"errors": ["Missing required refund request fields."]})
    assert route == "escalation"


def test_route_after_decision_sends_human_review_cases_to_review_node():
    route = route_after_decision({"needs_human_review": True, "refund_eligible": True, "status": "human_review"})
    assert route == "human_review"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest projects/refund_decision_agent/tests/test_graph_routing.py -q`
Expected: missing routing helpers or wrong route names.

- [ ] **Step 3: Write minimal graph wiring**

```python
# projects/refund_decision_agent/app/graph.py
from langgraph.graph import END, START, StateGraph

from app.nodes import (
    classify_refund_request_node,
    decide_refund_eligibility_node,
    eligible_response_node,
    escalation_response_node,
    human_review_required_node,
    ineligible_response_node,
    lookup_billing_evidence_node,
    persist_decision_node,
    retrieve_policy_context_node,
    validate_input_node,
)
from app.state import RefundDecisionState


def route_after_validation(state: RefundDecisionState) -> str:
    return "escalation" if state["errors"] else "classify"


def route_after_decision(state: RefundDecisionState) -> str:
    if state["needs_human_review"]:
        return "human_review"
    if state["refund_eligible"] is True:
        return "eligible"
    if state["refund_eligible"] is False:
        return "ineligible"
    return "escalation"


builder = StateGraph(RefundDecisionState)
builder.add_node("validate_input_node", validate_input_node)
builder.add_node("classify_refund_request_node", classify_refund_request_node)
builder.add_node("retrieve_policy_context_node", retrieve_policy_context_node)
builder.add_node("lookup_billing_evidence_node", lookup_billing_evidence_node)
builder.add_node("decide_refund_eligibility_node", decide_refund_eligibility_node)
builder.add_node("eligible_response_node", eligible_response_node)
builder.add_node("ineligible_response_node", ineligible_response_node)
builder.add_node("human_review_required_node", human_review_required_node)
builder.add_node("escalation_response_node", escalation_response_node)
builder.add_node("persist_decision_node", persist_decision_node)

builder.add_edge(START, "validate_input_node")
builder.add_conditional_edges(
    "validate_input_node",
    route_after_validation,
    {
        "classify": "classify_refund_request_node",
        "escalation": "escalation_response_node",
    },
)
builder.add_edge("classify_refund_request_node", "retrieve_policy_context_node")
builder.add_edge("retrieve_policy_context_node", "lookup_billing_evidence_node")
builder.add_edge("lookup_billing_evidence_node", "decide_refund_eligibility_node")
builder.add_conditional_edges(
    "decide_refund_eligibility_node",
    route_after_decision,
    {
        "eligible": "eligible_response_node",
        "ineligible": "ineligible_response_node",
        "human_review": "human_review_required_node",
        "escalation": "escalation_response_node",
    },
)
builder.add_edge("eligible_response_node", "persist_decision_node")
builder.add_edge("ineligible_response_node", "persist_decision_node")
builder.add_edge("human_review_required_node", "persist_decision_node")
builder.add_edge("escalation_response_node", "persist_decision_node")
builder.add_edge("persist_decision_node", END)

refund_decision_graph = builder.compile()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest projects/refund_decision_agent/tests/test_graph_routing.py -q`
Expected: routing helper and graph-path tests pass.

- [ ] **Step 5: Commit**

```bash
git add projects/refund_decision_agent/app/graph.py \
  projects/refund_decision_agent/tests/test_graph_routing.py
git commit -m "feat: wire refund decision graph routing"
```

## Milestone 4: API, Evals, Demos, And Project Setup

### Task 7: Add the FastAPI wrapper and API tests

**Files:**
- Modify: `projects/refund_decision_agent/app/api.py`
- Test: `projects/refund_decision_agent/tests/test_api.py`

- [ ] **Step 1: Write the failing API tests**

```python
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def test_refunds_decide_returns_structured_response():
    response = client.post(
        "/refunds/decide",
        json={
            "request_id": "REQ-API-001",
            "customer_id": "cust_001",
            "user_message": "I was charged twice for my subscription.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "REQ-API-001"
    assert body["needs_human_review"] is False
    assert "trace_events" not in body


def test_refunds_decide_debug_mode_returns_internal_fields():
    response = client.post(
        "/refunds/decide?debug=true",
        json={
            "request_id": "REQ-API-002",
            "customer_id": "cust_missing",
            "user_message": "Can you refund this unknown account?",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "workflow_path" in body
    assert "trace_events" in body
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest projects/refund_decision_agent/tests/test_api.py -q`
Expected: missing FastAPI app or incorrect response shaping.

- [ ] **Step 3: Write minimal API code**

```python
# projects/refund_decision_agent/app/api.py
from fastapi import FastAPI, Query

from app.graph import refund_decision_graph
from app.schemas import RefundDecisionRequest, RefundDecisionResponse

app = FastAPI(title="Refund Decision Agent", version="1.0.0")


def _initial_state(request: RefundDecisionRequest) -> dict:
    return {
        "request_id": request.request_id,
        "customer_id": request.customer_id,
        "user_message": request.user_message,
        "intent": None,
        "category": None,
        "risk_level": None,
        "retrieved_policy_docs": [],
        "billing_evidence": {},
        "customer_context": {},
        "refund_eligible": None,
        "refund_amount": None,
        "needs_human_review": False,
        "decision_reason": None,
        "policy_basis": [],
        "evidence_summary": None,
        "workflow_path": [],
        "trace_events": [],
        "errors": [],
        "final_response": None,
        "status": None,
        "final_node": None,
    }


@app.post("/refunds/decide")
def decide_refund(request: RefundDecisionRequest, debug: bool = Query(default=False)) -> dict:
    state = refund_decision_graph.invoke(_initial_state(request))
    response = RefundDecisionResponse(
        request_id=state["request_id"],
        customer_id=state["customer_id"],
        refund_eligible=state["refund_eligible"],
        refund_amount=state["refund_amount"],
        risk_level=state["risk_level"] or "high",
        needs_human_review=state["needs_human_review"],
        decision_reason=state["decision_reason"] or "No decision reason was produced.",
        policy_basis=state["policy_basis"],
        evidence_summary=state["evidence_summary"] or "",
        final_response=state["final_response"] or "",
        status=state["status"] or "escalated",
        workflow_path=state["workflow_path"],
        trace_events=state["trace_events"],
        errors=state["errors"],
        debug=debug or request.debug,
    )
    return response.public_dump()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest projects/refund_decision_agent/tests/test_api.py -q`
Expected: API tests pass in mock mode without env credentials.

- [ ] **Step 5: Commit**

```bash
git add projects/refund_decision_agent/app/api.py \
  projects/refund_decision_agent/tests/test_api.py
git commit -m "feat: add refund decision api"
```

### Task 8: Add eval runner, demos, environment, and Makefile/requirements support

**Files:**
- Modify: `projects/refund_decision_agent/evals/test_cases.json`
- Modify: `projects/refund_decision_agent/evals/run_eval.py`
- Modify: `projects/refund_decision_agent/scripts/run_demo.py`
- Modify: `projects/refund_decision_agent/scripts/run_policy_demo.py`
- Modify: `projects/refund_decision_agent/scripts/seed_data.py`
- Modify: `projects/refund_decision_agent/.env.example`
- Modify: `projects/refund_decision_agent/Makefile`
- Modify: `projects/refund_decision_agent/requirements.txt`
- Test: `projects/refund_decision_agent/tests/test_graph_routing.py`
- Test: `projects/refund_decision_agent/tests/test_safety.py`

- [ ] **Step 1: Write the failing eval and safety tests**

```python
import json
from pathlib import Path


def test_eval_cases_cover_required_scenarios():
    cases = json.loads(Path("projects/refund_decision_agent/evals/test_cases.json").read_text())
    labels = {case["request_id"] for case in cases}
    assert {"EVAL-001", "EVAL-002", "EVAL-003", "EVAL-004", "EVAL-005", "EVAL-006"} <= labels


def test_final_responses_never_claim_refund_was_issued():
    forbidden_phrases = {"refund issued", "we issued your refund", "refund has been processed"}
    # This assertion is paired with graph invocation in test_safety.py once the graph exists.
    assert forbidden_phrases
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest projects/refund_decision_agent/tests/test_safety.py -q`
Expected: missing eval coverage or safety assertions.

- [ ] **Step 3: Write minimal eval/demo/setup code**

```json
// projects/refund_decision_agent/evals/test_cases.json
[
  {
    "request_id": "EVAL-001",
    "customer_id": "cust_001",
    "user_message": "I was charged twice for my subscription. Can I get one charge refunded?",
    "expected_refund_eligible": true,
    "expected_needs_human_review": false,
    "expected_risk_level": "medium",
    "expected_final_node": "eligible_response_node"
  },
  {
    "request_id": "EVAL-002",
    "customer_id": "cust_002",
    "user_message": "I cancelled yesterday but was charged today. Can I get a refund?",
    "expected_refund_eligible": true,
    "expected_needs_human_review": false,
    "expected_risk_level": "medium",
    "expected_final_node": "eligible_response_node"
  },
  {
    "request_id": "EVAL-003",
    "customer_id": "cust_003",
    "user_message": "Can I get a refund for a charge from March?",
    "expected_refund_eligible": false,
    "expected_needs_human_review": false,
    "expected_risk_level": "low",
    "expected_final_node": "ineligible_response_node"
  },
  {
    "request_id": "EVAL-004",
    "customer_id": "cust_004",
    "user_message": "Please refund our annual enterprise subscription of $2,000.",
    "expected_refund_eligible": true,
    "expected_needs_human_review": true,
    "expected_risk_level": "high",
    "expected_final_node": "human_review_required_node"
  },
  {
    "request_id": "EVAL-005",
    "customer_id": "cust_005",
    "user_message": "Your records look wrong and I need a refund.",
    "expected_refund_eligible": null,
    "expected_needs_human_review": true,
    "expected_risk_level": "high",
    "expected_final_node": "human_review_required_node"
  },
  {
    "request_id": "EVAL-006",
    "customer_id": "cust_missing",
    "user_message": "I want a refund for this unknown account.",
    "expected_refund_eligible": null,
    "expected_needs_human_review": true,
    "expected_risk_level": "high",
    "expected_final_node": "escalation_response_node"
  }
]
```

```python
# projects/refund_decision_agent/evals/run_eval.py
import json
from pathlib import Path

from app.graph import refund_decision_graph


def build_state(case: dict) -> dict:
    return {
        "request_id": case["request_id"],
        "customer_id": case["customer_id"],
        "user_message": case["user_message"],
        "intent": None,
        "category": None,
        "risk_level": None,
        "retrieved_policy_docs": [],
        "billing_evidence": {},
        "customer_context": {},
        "refund_eligible": None,
        "refund_amount": None,
        "needs_human_review": False,
        "decision_reason": None,
        "policy_basis": [],
        "evidence_summary": None,
        "workflow_path": [],
        "trace_events": [],
        "errors": [],
        "final_response": None,
        "status": None,
        "final_node": None,
    }


def main() -> None:
    cases = json.loads(Path("evals/test_cases.json").read_text())
    passed = 0
    for case in cases:
        result = refund_decision_graph.invoke(build_state(case))
        ok = (
            result["refund_eligible"] == case["expected_refund_eligible"]
            and result["needs_human_review"] == case["expected_needs_human_review"]
            and result["risk_level"] == case["expected_risk_level"]
            and result["final_node"] == case["expected_final_node"]
            and "refund issued" not in (result["final_response"] or "").lower()
        )
        passed += int(ok)
        print(f"{case['request_id']}: {'PASS' if ok else 'FAIL'}")
    print(f"Summary: {passed}/{len(cases)} passed")


if __name__ == "__main__":
    main()
```

```python
# projects/refund_decision_agent/scripts/run_demo.py
from app.graph import refund_decision_graph


DEMO_CASES = [
    {"request_id": "DEMO-001", "customer_id": "cust_001", "user_message": "I was charged twice for my subscription."},
    {"request_id": "DEMO-002", "customer_id": "cust_002", "user_message": "I cancelled and was still charged."},
]


def build_state(case: dict) -> dict:
    return {
        "request_id": case["request_id"],
        "customer_id": case["customer_id"],
        "user_message": case["user_message"],
        "intent": None,
        "category": None,
        "risk_level": None,
        "retrieved_policy_docs": [],
        "billing_evidence": {},
        "customer_context": {},
        "refund_eligible": None,
        "refund_amount": None,
        "needs_human_review": False,
        "decision_reason": None,
        "policy_basis": [],
        "evidence_summary": None,
        "workflow_path": [],
        "trace_events": [],
        "errors": [],
        "final_response": None,
        "status": None,
        "final_node": None,
    }


for case in DEMO_CASES:
    result = refund_decision_graph.invoke(build_state(case))
    print(result["request_id"], result["status"], result["final_response"])
```

```python
# projects/refund_decision_agent/scripts/run_policy_demo.py
from app.policy_store import PolicyStore


def main() -> None:
    store = PolicyStore()
    docs = store.search("I was charged twice for my subscription.", intent="duplicate_charge_refund")
    for doc in docs:
        print(doc.section_ref)
        print(doc.content)
        print("---")


if __name__ == "__main__":
    main()
```

```python
# projects/refund_decision_agent/scripts/seed_data.py
from pathlib import Path


def main() -> None:
    Path("data/decision_records.json").write_text("[]\n")
    print("Reset data/decision_records.json")


if __name__ == "__main__":
    main()
```

```env
# projects/refund_decision_agent/.env.example
APP_ENV=local
CLASSIFIER_MODE=mock
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=refund-decision-agent
```

```makefile
# projects/refund_decision_agent/Makefile
.PHONY: install test eval demo run-api check

PYTHON := python
PIP := pip
UVICORN := uvicorn

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

test:
	pytest

eval:
	$(PYTHON) -m evals.run_eval

demo:
	$(PYTHON) scripts/run_demo.py

run-api:
	$(UVICORN) app.api:app --reload

check: test eval
```

```text
# projects/refund_decision_agent/requirements.txt
langgraph
langchain-core
langsmith
pydantic
python-dotenv
fastapi
uvicorn
pytest
typing-extensions
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest projects/refund_decision_agent/tests/test_safety.py -q`
Expected: safety/eval fixture tests pass.

- [ ] **Step 5: Commit**

```bash
git add projects/refund_decision_agent/evals/test_cases.json \
  projects/refund_decision_agent/evals/run_eval.py \
  projects/refund_decision_agent/scripts/run_demo.py \
  projects/refund_decision_agent/scripts/run_policy_demo.py \
  projects/refund_decision_agent/scripts/seed_data.py \
  projects/refund_decision_agent/.env.example \
  projects/refund_decision_agent/Makefile \
  projects/refund_decision_agent/requirements.txt \
  projects/refund_decision_agent/tests/test_safety.py
git commit -m "feat: add refund evals demos and project setup"
```

### Task 9: Align README and PRD with JSON-only v1 persistence and honest scope

**Files:**
- Modify: `projects/refund_decision_agent/README.md`
- Modify: `projects/refund_decision_agent/docs/refund_decision_agent_prd.md`

- [ ] **Step 1: Write the failing documentation assertions**

```python
from pathlib import Path


def test_readme_mentions_json_decision_records_not_sqlite_default():
    readme = Path("projects/refund_decision_agent/README.md").read_text().lower()
    assert "decision_records.json" in readme
    assert "sqlite" not in readme or "future improvement" in readme
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest projects/refund_decision_agent/tests/test_safety.py -q`
Expected: README/PRD still mention SQLite as current storage.

- [ ] **Step 3: Update the docs**

```md
<!-- projects/refund_decision_agent/README.md -->
This project uses synthetic local JSON fixtures and persists decision history to `data/decision_records.json`.

The workflow does not execute real refunds, does not connect to real payment systems, and does not claim production-grade persistence. SQLite and richer persistence can be added later as future improvements.
```

```md
<!-- projects/refund_decision_agent/docs/refund_decision_agent_prd.md -->
Expected local data sources:

data/
├── policies/
│   ├── refund_policy.md
│   ├── cancellation_policy.md
│   └── billing_policy.md
├── mock_billing_records.json
├── mock_customers.json
└── decision_records.json

Decision persistence in v1 is append-only JSON for demo transparency. SQLite is a possible future improvement and is not part of the default implementation scope.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest projects/refund_decision_agent/tests/test_safety.py -q`
Expected: doc-alignment assertions pass.

- [ ] **Step 5: Commit**

```bash
git add projects/refund_decision_agent/README.md \
  projects/refund_decision_agent/docs/refund_decision_agent_prd.md \
  projects/refund_decision_agent/tests/test_safety.py
git commit -m "docs: align refund agent docs with json persistence"
```

## Milestone 5: Full Verification And Cleanup

### Task 10: Run the project verification sequence and tighten gaps

**Files:**
- Modify: any `projects/refund_decision_agent/` file required by failing verification

- [ ] **Step 1: Create the local virtual environment**

Run: `cd projects/refund_decision_agent && python3 -m venv .venv`
Expected: `.venv/` created locally for isolated verification.

- [ ] **Step 2: Install dependencies**

Run: `cd projects/refund_decision_agent && source .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt`
Expected: install succeeds without requiring `OPENAI_API_KEY`.

- [ ] **Step 3: Run the test suite**

Run: `cd projects/refund_decision_agent && source .venv/bin/activate && make test`
Expected: all pytest tests pass.

- [ ] **Step 4: Run evals**

Run: `cd projects/refund_decision_agent && source .venv/bin/activate && make eval`
Expected: all eval cases pass and summary reports `6/6 passed`.

- [ ] **Step 5: Run the demo**

Run: `cd projects/refund_decision_agent && source .venv/bin/activate && make demo`
Expected: sample requests print structured, non-committal final responses.

- [ ] **Step 6: Run the API locally**

Run: `cd projects/refund_decision_agent && source .venv/bin/activate && make run-api`
Expected: Uvicorn starts locally at `http://127.0.0.1:8000`.

- [ ] **Step 7: Verify the endpoint manually**

Run:

```bash
curl -X POST "http://127.0.0.1:8000/refunds/decide" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "REQ-001",
    "customer_id": "cust_001",
    "user_message": "I was charged twice for my subscription. Can I get one charge refunded?"
  }'
```

Expected: a JSON response with `refund_eligible: true`, `needs_human_review: false`, and a final response that does not claim a refund was issued.

- [ ] **Step 8: Fix any failing verification gaps immediately**

```python
# Example final cleanup target if safety wording fails.
SAFE_RESPONSE_PHRASES = {
    "eligible": "You appear eligible for a refund review based on the demo policy and billing evidence.",
    "review": "This request needs manual review under the demo policy.",
    "escalated": "The available demo evidence is incomplete or conflicting, so this request needs follow-up review.",
}
```

- [ ] **Step 9: Commit the final verification fixes**

```bash
git add projects/refund_decision_agent
git commit -m "test: verify refund decision agent end to end"
```

## Self-Review Checklist

- Every implemented path must end in `persist_decision_node`, including validation/error cases via `escalation_response_node`.
- `projects/refund_decision_agent/data/decision_records.json` is the only persistence path in v1.
- `CLASSIFIER_MODE=mock` remains the default and sufficient for local tests, evals, demos, and API usage.
- No test, eval, or demo should require real payment systems or real customer data.
- No final response should say a refund was issued, processed, or executed.
- README and PRD must describe JSON persistence as current behavior and SQLite only as future work.
