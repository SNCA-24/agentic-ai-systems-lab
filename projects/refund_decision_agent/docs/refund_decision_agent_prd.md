# Product Requirements Document: Refund Decision Agent

## 1. Product Summary

The Refund Decision Agent is a portfolio-grade agentic workflow that evaluates refund requests using policy-grounded retrieval, mock billing/customer evidence, structured refund eligibility decisions, deterministic graph routing, JSON decision persistence, and local evaluation.

The project is designed as Project 2 in the `agentic-ai-systems-lab` monorepo and builds on Project 1’s graph-orchestration foundation. Unlike the Support Ticket Triage Agent, which focuses on classification, routing, HITL previews, and approval safety, this project focuses on **RAG + tool-using decisioning** for a realistic refund workflow.

The agent does **not** execute real refunds. It only determines refund eligibility, explains the decision using synthetic policy and mock billing evidence, and flags high-risk or ambiguous cases for human review.

---

## 2. Problem Statement

Refund requests are common in SaaS, subscription, marketplace, and fintech-style customer support workflows. A refund decision often depends on both:

1. **Policy knowledge** — refund policy, cancellation policy, billing policy, enterprise account rules, duplicate-charge rules, refund-window rules.
2. **Customer-specific evidence** — billing records, cancellation timestamp, subscription status, charge history, refund history, and customer/account type.

A naive LLM-only system may hallucinate policy, ignore billing facts, overpromise refunds, or fail to escalate high-value or ambiguous cases.

This project solves that by designing a controlled graph workflow where:

- RAG retrieves relevant synthetic policy context.
- Mock read-only tools retrieve customer and billing evidence.
- Structured decision logic produces a refund eligibility decision.
- Deterministic routing handles eligible, ineligible, high-risk, and unclear cases.
- Human-review flags prevent unsupported automation for risky scenarios.
- Evaluation verifies decision-path correctness, not just response wording.

---

## 3. Goals

### 3.1 Primary Goals

- Build a LangGraph-based refund decision workflow.
- Retrieve refund/cancellation/billing policy context from local Markdown files.
- Use mock read-only tools to inspect synthetic customer and billing records.
- Produce structured refund eligibility decisions using Pydantic schemas.
- Route cases deterministically based on eligibility, evidence quality, risk level, and human-review need.
- Provide customer-safe final responses grounded in policy and mock evidence.
- Add local evals for refund scenarios and routing behavior.
- Add workflow-path and trace-event observability hooks.
- Keep the project cost-safe through mock mode by default.
- Keep the project honest by avoiding real refund execution or real payment integration.

### 3.2 Portfolio Goals

- Demonstrate RAG + tool-using agent architecture.
- Demonstrate typed state and structured AI outputs.
- Demonstrate deterministic graph control with clean extension points for future model-assisted decisions.
- Demonstrate safety boundaries for financial workflows.
- Demonstrate local evaluation and LangSmith-ready observability.
- Produce a clean README, PRD, tests, evals, and demo flow suitable for GitHub and portfolio review.

---

## 4. Non-Goals / Out of Scope

The following are explicitly out of scope for v1:

- Real refund execution.
- Real payment processor integration.
- Real customer, billing, subscription, or payment data.
- Production authentication or RBAC.
- Production-grade database persistence as a hard requirement.
- Real approval workflow execution.
- Hosted production deployment claims.
- Large-scale vector database retrieval as the default implementation.
- Automatic refund approval for high-value or ambiguous cases.

The project may include future design hooks for these capabilities, but v1 should not claim they are implemented unless they are actually working.

---

## 5. Target Users

### 5.1 Primary Portfolio Audience

- AI Engineer hiring managers.
- LLM Engineer interviewers.
- Agentic AI / Applied AI reviewers.
- ML/AI platform engineers reviewing project architecture.

### 5.2 Simulated Product Users

- Customer support operations teams.
- Billing support analysts.
- Refund operations reviewers.
- Internal support tooling teams.

---

## 6. User Personas

### 6.1 Support Agent

A support agent wants to understand whether a customer appears eligible for a refund and what evidence supports the decision.

Needs:

- clear refund decision
- policy basis
- billing evidence summary
- risk level
- human-review flag when required

### 6.2 Support Manager

A support manager wants high-value or unclear refund cases escalated instead of auto-decided.

Needs:

- high-risk flag
- decision trail
- policy and evidence summary
- review recommendation

### 6.3 AI Engineer Reviewer

A portfolio reviewer wants to see whether the project demonstrates real agentic engineering, not just prompt demos.

Needs:

- graph architecture
- typed state
- RAG component
- tool-use boundary
- evals/tests
- observability hooks
- honest scope limitations

---

## 7. Core Product Scope

The Refund Decision Agent should implement a single main workflow:

```text
refund request
→ validate input
→ classify refund intent
→ retrieve relevant policy context
→ lookup mock billing/customer evidence
→ make structured refund eligibility decision
→ route by decision and risk
   ├── eligible_low_risk → eligible_response_node
   ├── eligible_high_value → human_review_required_node
   ├── ineligible → ineligible_response_node
   └── unclear_policy_or_missing_data → escalation_response_node
→ persist one JSON decision record
→ return grounded response
```

The core workflow should be understandable, testable, and locally runnable.

---

## 8. Core Design Principles

### 8.1 RAG Retrieves Policy Knowledge

The agent should not answer refund policy questions from generic model memory. It should retrieve relevant policy snippets from local synthetic policy files.

Expected policy files:

```text
data/policies/refund_policy.md
data/policies/cancellation_policy.md
data/policies/billing_policy.md
```

### 8.2 Tools Retrieve Customer and Billing Facts

The LLM should not invent charge history, cancellation status, duplicate charges, or customer context. The workflow should call mock read-only tools backed by local JSON fixtures.

### 8.3 Structured Decisioning Controls Output

Refund decisions should be represented as structured data, not only prose.

Example decision fields:

- `refund_eligible`
- `refund_amount`
- `risk_level`
- `needs_human_review`
- `decision_reason`
- `policy_basis`
- `evidence_summary`

### 8.4 Deterministic Routing Controls Workflow

Any future LLM-assisted classification or decisioning must remain outside the default path. Deterministic code must decide graph routes in v1.

Example:

```text
if needs_human_review == true:
    route to human_review_required_node
elif refund_eligible == true:
    route to eligible_response_node
elif refund_eligible == false:
    route to ineligible_response_node
else:
    route to escalation_response_node
```

### 8.5 No Real Write Actions in v1

All tools in v1 should be read-only. The project may flag when a human review is needed but should not issue, simulate as real, or claim to execute refunds.

### 8.6 Evaluate the Path, Not Just the Answer

The system should evaluate:

- policy retrieval
- billing evidence lookup
- eligibility correctness
- risk routing
- final node correctness
- human-review flag correctness

A nice final response is not enough if the internal decision path is wrong.

---

## 9. Functional Requirements

### FR-001: Input Validation

The system must validate that each request includes:

- `request_id`
- `customer_id`
- `user_message`

If required fields are missing or empty, the workflow should route to a safe error/escalation response.

Acceptance criteria:

- Empty user messages do not crash the graph.
- Missing customer IDs are handled safely.
- Validation errors are stored in graph state.
- Validation failures produce customer-safe responses.

---

### FR-002: Refund Intent Classification

The system must classify the user request into a refund-related intent.

Expected intent examples:

- `duplicate_charge_refund`
- `post_cancellation_charge_refund`
- `general_refund_request`
- `refund_window_question`
- `enterprise_refund_request`
- `unclear_refund_request`
- `non_refund_billing_question`

Acceptance criteria:

- Classification result is structured.
- Classification includes confidence or equivalent metadata where available.
- Classification result is stored in graph state.
- Mock mode should provide deterministic classifications for local tests.

---

### FR-003: Policy Retrieval

The system must retrieve relevant policy context from local Markdown policy files.

Expected policies:

- refund policy
- cancellation policy
- billing policy

Acceptance criteria:

- Relevant policy snippets are returned for duplicate-charge requests.
- Relevant policy snippets are returned for post-cancellation charge requests.
- Relevant policy snippets are returned for refund-window requests.
- Retrieved documents include source metadata such as file name or section label.
- Retrieved policy docs are stored in state.

---

### FR-004: Mock Billing / Customer Evidence Lookup

The system must call read-only mock tools to collect evidence.

Expected tools:

- `lookup_customer_profile(customer_id)`
- `lookup_subscription_status(customer_id)`
- `lookup_recent_charges(customer_id)`
- `lookup_cancellation_timestamp(customer_id)`
- `lookup_refund_history(customer_id)`

Acceptance criteria:

- Tools read from local fixtures only.
- Tools do not modify any external system.
- Missing customer records are handled safely.
- Tool outputs are structured and stored in graph state.
- Tool failures are captured in `errors` or equivalent state.

---

### FR-005: Structured Refund Eligibility Decision

The system must produce a structured decision that combines policy context and mock billing evidence.

Required decision fields:

- `refund_eligible`
- `refund_amount`
- `risk_level`
- `needs_human_review`
- `decision_reason`
- `policy_basis`
- `evidence_summary`

Acceptance criteria:

- Duplicate-charge scenarios can be marked eligible when billing evidence supports the claim.
- Post-cancellation charge scenarios can be marked eligible when policy and charge timing support the claim.
- Out-of-window refund scenarios can be marked ineligible.
- High-value refund scenarios can be marked eligible but requiring human review.
- Unclear or conflicting evidence routes to escalation or human review.

---

### FR-006: Deterministic Decision Routing

The graph must route the workflow based on structured decision fields.

Routes:

- `eligible_response_node`
- `ineligible_response_node`
- `human_review_required_node`
- `escalation_response_node`

Acceptance criteria:

- Low/medium-risk eligible refunds route to `eligible_response_node`.
- Ineligible refunds route to `ineligible_response_node`.
- High-value, enterprise, ambiguous, or conflicting cases route to `human_review_required_node` or `escalation_response_node`.
- Routing logic is implemented in deterministic Python functions, not free-form LLM output.

---

### FR-007: Grounded Final Response

The system must return a customer-safe response based on the decision path.

Response should include:

- high-level outcome
- policy/evidence basis
- human-review status when needed
- no unsupported promise that a real refund was issued

Acceptance criteria:

- The response does not claim that a refund was executed.
- The response distinguishes eligibility from actual refund processing.
- Human-review cases clearly state that review is required.
- Ineligible cases explain the reason without overexposing internal implementation details.

---

### FR-008: Decision Record Persistence

The system should support local persistence of decision records where implemented.

Expected v1 storage:

- append-only JSON decision records at `projects/refund_decision_agent/data/decision_records.json`

Acceptance criteria:

- Decision record includes request ID, customer ID, decision outcome, risk level, human-review flag, final node, and timestamp where available.
- Persistence failure does not crash the entire workflow.
- Stored records must not contain secrets or real payment data.

---

### FR-009: Workflow Path and Trace Events

The system must track path-level observability.

Expected state fields:

- `workflow_path`
- `trace_events`

Acceptance criteria:

- Each major node appends itself to `workflow_path`.
- Important events are appended to `trace_events`.
- Trace metadata avoids sensitive data.
- Eval runner can inspect the terminal business response node from `final_node`.

---

### FR-010: FastAPI Endpoint

The project should expose the workflow through a local FastAPI endpoint.

Suggested endpoint:

```text
POST /refunds/decide
```

Example request:

```json
{
  "request_id": "REQ-001",
  "customer_id": "cust_001",
  "user_message": "I was charged twice for my subscription. Can I get one charge refunded?"
}
```

Example response:

```json
{
  "request_id": "REQ-001",
  "customer_id": "cust_001",
  "refund_eligible": true,
  "refund_amount": 29.0,
  "risk_level": "medium",
  "needs_human_review": false,
  "final_response": "You appear eligible for a refund for the duplicate charge based on the policy and billing evidence in this demo system."
}
```

Acceptance criteria:

- API validates request payload using Pydantic.
- API invokes the graph.
- API returns structured response.
- API does not expose raw internal trace unless explicitly included for debug mode.

---

### FR-011: Local Eval Runner

The project must include an eval runner that checks refund decision behavior.

Eval scenarios should include:

- duplicate charge refund
- charge after cancellation
- refund outside allowed window
- high-value enterprise refund
- unclear or conflicting billing evidence
- missing customer record

Acceptance criteria:

- Eval runner loads `evals/test_cases.json`.
- Eval runner invokes the graph for each case.
- Eval runner checks refund eligibility, risk level, human-review flag, and expected final node.
- Eval runner prints pass/fail summary.
- Eval runner can run in mock mode without API cost.

---

### FR-012: Test Coverage

The project must include pytest coverage for core modules.

Expected test files:

- `tests/test_graph_routing.py`
- `tests/test_policy_store.py`
- `tests/test_refund_tools.py`
- `tests/test_decision_engine.py`
- `tests/test_safety.py`
- `tests/test_api.py`

Acceptance criteria:

- Tests run with `make test`.
- Core decision rules are testable without live LLM calls.
- Tests should verify that no real refund execution exists in v1.
- Tests should verify that high-value cases require human review.

---

## 10. Non-Functional Requirements

### NFR-001: Cost-Safe Local Execution

The default mode should not require live LLM calls.

Acceptance criteria:

- `CLASSIFIER_MODE=mock` or equivalent mode is available.
- Tests and evals can run without `OPENAI_API_KEY`.
- Live LLM integration, if added later, should be opt-in and isolated from the default path.

---

### NFR-002: Observability

The system should support local trace events and LangSmith-ready configuration.

Acceptance criteria:

- `.env.example` includes LangSmith variables.
- Trace metadata includes node names and event types.
- LangSmith tracing can be enabled when credentials are configured.
- Local trace events remain useful without LangSmith.

---

### NFR-003: Security and Privacy Boundaries

The system must not include real customer/payment data.

Acceptance criteria:

- All data is synthetic.
- `.env` is ignored by Git.
- Trace events do not include secrets.
- README clearly states no real refund execution.

---

### NFR-004: Maintainability

The repository should have clear module boundaries.

Acceptance criteria:

- Graph wiring lives in `app/graph.py`.
- Nodes live in `app/nodes.py`.
- State schemas live in `app/state.py`.
- Pydantic models live in `app/schemas.py`.
- Mock tools live in `app/tools.py`.
- Retrieval logic lives in `app/policy_store.py`.
- Decision rules live in `app/decision_engine.py`.

---

### NFR-005: Reproducibility

The project must be runnable from a clean local environment.

Acceptance criteria:

- `requirements.txt` exists.
- `Makefile` provides `install`, `test`, `eval`, `demo`, `run-api`, and `check` targets.
- `.env.example` exists.
- README quickstart commands work on macOS/zsh.

---

## 11. State Model Requirements

The graph state should support at least the following fields:

```python
class RefundDecisionState(TypedDict):
    request_id: str
    customer_id: str
    user_message: str

    intent: Optional[str]
    category: Optional[str]
    risk_level: Optional[str]

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
```

The state should be inspectable after graph execution and usable for evals.

---

## 12. Schema Requirements

The project should define Pydantic schemas for:

### 12.1 Refund Intent Classification

Fields:

- `intent`
- `category`
- `confidence`
- `decision_summary`

### 12.2 Retrieved Policy Document

Fields:

- `doc_id`
- `title`
- `source`
- `content_snippet`
- `relevance_score`

### 12.3 Billing Lookup Result

Fields:

- `customer_id`
- `subscription_status`
- `recent_charges`
- `cancellation_timestamp`
- `refund_history`
- `evidence_status`

### 12.4 Refund Eligibility Decision

Fields:

- `refund_eligible`
- `refund_amount`
- `risk_level`
- `needs_human_review`
- `decision_reason`
- `policy_basis`
- `evidence_summary`

### 12.5 API Request / Response Schemas

Request fields:

- `request_id`
- `customer_id`
- `user_message`

Response fields:

- `request_id`
- `customer_id`
- `status`
- `refund_eligible`
- `refund_amount`
- `risk_level`
- `needs_human_review`
- `decision_reason`
- `final_response`

---

## 13. Policy Corpus Requirements

The synthetic policy corpus should include realistic but simple rules.

### 13.1 Refund Policy

Should cover:

- duplicate charges are refundable when confirmed
- refund requests inside allowed window
- refund requests outside allowed window
- high-value refund threshold requiring review
- enterprise refunds requiring review

### 13.2 Cancellation Policy

Should cover:

- cancellation timestamp handling
- charge-after-cancellation scenarios
- pending charges versus finalized charges
- refund eligibility after confirmed cancellation

### 13.3 Billing Policy

Should cover:

- recurring subscription charges
- invoice timing
- duplicate charge detection
- prorated charge assumptions where needed

---

## 14. Mock Data Requirements

### 14.1 Mock Customers

The mock customer file should include examples such as:

- standard customer
- enterprise customer
- cancelled customer
- missing/unknown customer
- customer with prior refund history

### 14.2 Mock Billing Records

The mock billing records should include examples such as:

- duplicate charge
- charge after cancellation
- normal valid charge
- high-value annual subscription charge
- charge outside refund window
- conflicting or missing billing evidence

---

## 15. Routing Rules

The decision router should follow deterministic rules.

| Condition | Expected Route |
|---|---|
| `refund_eligible=true` and `needs_human_review=false` | `eligible_response_node` |
| `refund_eligible=true` and `needs_human_review=true` | `human_review_required_node` |
| `refund_eligible=false` and evidence is sufficient | `ineligible_response_node` |
| evidence missing, policy unclear, or decision uncertain | `escalation_response_node` |
| validation error | `escalation_response_node` or safe error node |

---

## 16. Safety Requirements

### SR-001: No Real Refund Execution

The system must not include any function that performs real financial refunds.

### SR-002: No Unsupported Refund Claims

Final responses must not say a refund has been issued.

Allowed wording:

```text
You appear eligible for a refund based on the available demo evidence.
```

Not allowed:

```text
Your refund has been issued.
```

### SR-003: High-Value Review Gate

High-value refund cases must require human review.

### SR-004: Ambiguous Evidence Escalation

Missing, conflicting, or unclear evidence must route to escalation or review.

### SR-005: Policy Grounding

Policy-sensitive decisions must reference retrieved policy basis in state and decision output.

---

## 17. Evaluation Requirements

The eval runner should check both outputs and workflow behavior.

Minimum eval fields:

```json
{
  "request_id": "EVAL-001",
  "customer_id": "cust_001",
  "user_message": "I was charged twice for my subscription. Can I get one charge refunded?",
  "expected_refund_eligible": true,
  "expected_needs_human_review": false,
  "expected_risk_level": "medium",
  "expected_final_node": "eligible_response_node"
}
```

Eval checks:

- refund eligibility correctness
- risk level correctness
- human-review correctness
- expected final node correctness
- policy basis present for policy-grounded decisions
- no unsupported execution claim in final response

---

## 18. API Requirements

### 18.1 Endpoint

```text
POST /refunds/decide
```

### 18.2 Request Body

```json
{
  "request_id": "REQ-001",
  "customer_id": "cust_001",
  "user_message": "I cancelled yesterday but was charged today. Can I get a refund?"
}
```

### 18.3 Response Body

```json
{
  "request_id": "REQ-001",
  "customer_id": "cust_001",
  "status": "eligible",
  "refund_eligible": true,
  "refund_amount": 29.0,
  "risk_level": "medium",
  "needs_human_review": false,
  "decision_reason": "The retrieved cancellation policy and mock billing evidence indicate the charge occurred after cancellation.",
  "final_response": "You appear eligible for a refund based on the cancellation policy and billing evidence available in this demo system."
}
```

### 18.4 Status Values

Expected status values:

- `eligible`
- `human_review`
- `ineligible`
- `escalated`

---

## 19. Observability Requirements

### 19.1 Workflow Path

Each node should append its name to `workflow_path`.

Example:

```json
[
  "validate_input_node",
  "classify_refund_request_node",
  "retrieve_policy_context_node",
  "lookup_billing_evidence_node",
  "decide_refund_eligibility_node",
  "eligible_response_node",
  "persist_decision_node"
]
```

### 19.2 Trace Events

Trace events should include:

- node name
- event type
- message
- metadata

Example:

```json
{
  "node": "retrieve_policy_context_node",
  "event_type": "policy_retrieval_completed",
  "message": "Retrieved refund policy context.",
  "metadata": {
    "doc_count": 2,
    "sources": ["refund_policy.md", "billing_policy.md"]
  }
}
```

### 19.3 LangSmith Configuration

`.env.example` should include:

```text
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=refund-decision-agent
```

LangSmith should be optional and should not be required for local tests.

---

## 20. Success Metrics

### 20.1 Functional Success

- The demo workflow runs locally.
- Eval runner completes successfully.
- Core refund scenarios route to expected final nodes.
- High-value cases require human review.
- Ineligible cases do not produce eligibility claims.
- Missing evidence routes to escalation.

### 20.2 Engineering Success

- Tests run with `make test`.
- Evals run with `make eval`.
- Full local check runs with `make check`.
- API runs with `make run-api`.
- README and PRD accurately reflect implemented scope.
- Default mode is cost-safe.

### 20.3 Portfolio Success

- Reviewer can understand the architecture within 2 minutes.
- Reviewer can run the demo locally.
- Reviewer can see RAG, tools, graph routing, evals, and observability hooks.
- The project makes honest claims and does not overstate production readiness.

---

## 21. Milestones

### Milestone 1: Project Skeleton

Deliverables:

- repository structure
- README
- PRD
- `.env.example`
- `requirements.txt`
- Makefile
- synthetic policy files
- mock data placeholders

Exit criteria:

- files exist in expected locations
- project can install dependencies

---

### Milestone 2: Mock Data and Policy Store

Deliverables:

- synthetic policy documents
- mock customer records
- mock billing records
- `policy_store.py`
- policy retrieval tests

Exit criteria:

- policy retrieval returns relevant snippets for known scenarios
- tests pass for policy lookup behavior

---

### Milestone 3: Read-Only Tools

Deliverables:

- customer profile lookup
- subscription status lookup
- recent charges lookup
- cancellation timestamp lookup
- refund history lookup
- tool tests

Exit criteria:

- tools return structured outputs
- missing customer/tool failure paths are covered

---

### Milestone 4: Core LangGraph Workflow

Deliverables:

- state model
- schemas
- nodes
- graph wiring
- deterministic routing
- demo script

Exit criteria:

- demo request flows through expected nodes
- eligible/ineligible/review/escalation routes work locally

---

### Milestone 5: Evaluation and Tests

Deliverables:

- eval test cases
- eval runner
- pytest tests for routing, policy store, tools, decision engine, safety, and API

Exit criteria:

- `make test` passes
- `make eval` passes
- high-risk and unclear cases are covered

---

### Milestone 6: API and Observability

Deliverables:

- FastAPI endpoint
- trace events
- workflow path output for debug mode
- LangSmith-ready config
- documentation updates

Exit criteria:

- API returns structured refund decision response
- local trace events are inspectable
- LangSmith can be enabled through environment variables

---

## 22. V1 Defaults and Future Questions

Resolved v1 defaults:

1. The critical path uses deterministic mock decision rules with `CLASSIFIER_MODE=mock` as the default.
2. JSON decision records are the v1 default; SQLite remains a future improvement only.
3. Policy retrieval uses lightweight local scoring over Markdown policy sections.
4. API debug responses may expose `workflow_path`, `trace_events`, and `errors` when debug mode is explicitly enabled.
5. Human-review cases remain flag-only in v1; there is no review execution endpoint.

Future questions:

- Should a live LLM classifier be added later behind isolated, opt-in configuration?
- Should policy retrieval move from keyword scoring to embedding-based ranking?
- Should a later version add a simulated reviewer workflow on top of the existing `human_review` route?

---

## 23. Final Scope Statement

The Refund Decision Agent v1 is a policy-grounded, graph-orchestrated refund decision workflow. It demonstrates how an AI system can combine local RAG, mock read-only billing tools, structured decision outputs, deterministic routing, human-review flags, and evaluation without executing real financial actions.

The project is intentionally scoped to be realistic, safe, inspectable, and portfolio-ready while avoiding claims of production payment automation.
