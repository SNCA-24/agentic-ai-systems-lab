# Refund Decision Agent

A LangGraph-based refund decision agent that combines local policy retrieval, mock billing evidence, deterministic refund eligibility logic, structured responses, JSON decision persistence, local evals, and LangSmith-ready observability.

---

## Tech Stack Snapshot

- **Agent Orchestration:** LangGraph, typed graph state, deterministic routing
- **Decisioning / Schemas:** deterministic Python logic, Pydantic schemas, `CLASSIFIER_MODE=mock` by default
- **RAG / Policy Grounding:** local Markdown policy store, policy retrieval, policy-backed decision context
- **Backend / API:** Python, FastAPI, Uvicorn
- **Data / Persistence:** local JSON fixtures, mock customer and billing records, append-only JSON decision records
- **Evaluation / Observability:** pytest, local eval runner, workflow path checks, trace events, LangSmith-ready config
- **Engineering:** Makefile, demo scripts, Docker-ready structure, `.env.example`, CI-friendly local execution

---

## Why This Project Exists

Refund decisions are a common enterprise workflow where an AI system should not rely on generic model knowledge or free-form reasoning alone.

A reliable refund agent needs to answer questions such as:

- What does the refund or cancellation policy actually say?
- Was the customer charged after cancellation?
- Was the charge duplicated?
- Is the refund amount low risk or high value?
- Does the case require human review before action?
- What evidence supports the decision?

This project exists to move beyond simple ticket classification and demonstrate a more realistic agentic workflow: **policy-grounded decisioning with retrieval, mock system evidence, structured outputs, deterministic routing, and evaluation**.

---

## What This Project Builds

This project builds a refund decision workflow, not a real payment processor.

The system implements:

- a LangGraph workflow for refund request handling
- a local policy retrieval layer over synthetic refund, cancellation, and billing policies
- mock read-only tools for customer, subscription, billing, charge, and refund-history evidence
- a structured refund eligibility decision step
- deterministic routing for eligible, ineligible, high-risk, and unclear cases
- human-review flags for high-value or ambiguous refund requests
- local decision-path tracing through `workflow_path` and `trace_events`
- a FastAPI endpoint for refund decision requests
- append-only JSON persistence at `data/decision_records.json`
- local evals and pytest coverage for policy-grounded behavior

This project does **not** execute real refunds or connect to real billing systems.

---

## Architecture / Workflow

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
→ persist decision record
→ return grounded response
```

### Core Principle

```text
RAG retrieves policy knowledge.
Tools retrieve customer and billing facts.
Structured decision logic evaluates eligibility.
Deterministic graph routing controls the workflow.
Human review is required for high-risk or ambiguous cases.
```

---

## Key Features

### Agent Workflow Features

- Typed LangGraph state for refund decision workflows
- Structured refund intent classification with deterministic mock logic
- Policy retrieval node for refund, cancellation, and billing policies
- Mock billing evidence lookup through read-only tools
- Deterministic risk routing after structured decision output
- Human-review path for high-value, enterprise, or ambiguous refunds

### RAG / Policy-Grounding Features

- Local Markdown policy files under `data/policies/`
- Policy retrieval through `app/policy_store.py`
- Retrieved policy snippets stored in graph state
- Decision outputs linked to policy basis
- Synthetic policy examples for duplicate charges, post-cancellation charges, refund windows, and high-value review thresholds

### Tool Safety Features

- Read-only mock tools only in v1
- No real refund execution
- No real payment API integration
- Explicit separation between policy retrieval, billing lookup, and decision routing
- Human-review flag before any future write-action path

### Evaluation / Observability Features

- Local eval set for policy-grounded refund scenarios
- Workflow-path checks for routing correctness
- Trace events for decision debugging
- LangSmith-ready environment configuration
- Cost-safe mock mode for repeatable local and CI runs

---

## Technical Implementation

### Core Components

| Component | Purpose |
|---|---|
| `app/graph.py` | Builds the LangGraph refund decision workflow |
| `app/state.py` | Defines typed graph state for refund requests, policy context, evidence, decisions, traces, and errors |
| `app/schemas.py` | Defines Pydantic schemas for API payloads, retrieved policy documents, billing evidence, responses, and persisted decision records |
| `app/nodes.py` | Implements graph nodes for validation, classification, retrieval, evidence lookup, decisioning, routing, and responses |
| `app/policy_store.py` | Loads and retrieves relevant local policy snippets |
| `app/tools.py` | Provides mock read-only customer, subscription, billing, and refund-history tools |
| `app/decision_engine.py` | Applies deterministic risk and review rules around structured refund decisions |
| `app/tracing.py` | Adds workflow path and trace-event helpers |
| `app/api.py` | Exposes the refund decision workflow through FastAPI |
| `evals/run_eval.py` | Runs local evaluation over refund decision test cases |

### Supported Execution Path

The implemented v1 execution path is:

```text
API/demo request
→ graph invocation
→ deterministic mock classification
→ policy retrieval
→ mock billing evidence lookup
→ deterministic eligibility decision
→ deterministic graph route
→ terminal response node
→ `persist_decision_node`
→ customer-safe response
```

### Verification Hooks

The repository includes:

- `pytest` tests for policy retrieval, tools, decision rules, safety behavior, and API responses
- local eval runner for policy-grounded decision cases
- demo scripts for end-to-end graph and policy retrieval output
- mock mode for cost-safe CI and local testing
- LangSmith-ready tracing metadata for interactive debugging when credentials are configured

---

## Data / Inputs / Assumptions

This project uses synthetic local data only.

Local data sources:

```text
data/
├── policies/
│   ├── refund_policy.md
│   ├── cancellation_policy.md
│   └── billing_policy.md
├── mock_billing_records.json
├── mock_customers.json
└── decision_records.json
```

### Assumptions

- Policy documents are synthetic and written for demonstration purposes.
- Customer and billing records are mocked fixtures.
- Refund eligibility is evaluated against simplified local policy rules.
- High-value or ambiguous refunds are routed to human review instead of auto-approval.
- No real customer, payment, billing, or subscription data is used.

---

## Methodology / Approach

This project uses a **RAG + tool-using decision workflow**.

The approach is:

1. Classify the user request into a refund-related intent.
2. Retrieve relevant refund, cancellation, or billing policy snippets.
3. Call mock read-only tools to collect customer and charge evidence.
4. Produce a structured refund eligibility decision.
5. Apply deterministic risk and human-review rules.
6. Route to the appropriate response path.
7. Persist one structured decision record for debugging and evaluation.

The critical path is deterministic. `CLASSIFIER_MODE=mock` is the default, and tests, evals, demos, and local API runs do not require `OPENAI_API_KEY`.

---

## Evaluation / Results

The project should evaluate more than final response quality.

Current evaluation dimensions:

| Evaluation Area | What It Checks |
|---|---|
| Intent classification | Whether refund, duplicate charge, cancellation, billing, or unclear intents are identified correctly |
| Policy retrieval | Whether the correct policy snippet is retrieved for the scenario |
| Billing evidence usage | Whether mock billing facts are incorporated into the decision |
| Refund eligibility | Whether eligible/ineligible outcomes match expected cases |
| Human-review routing | Whether high-value or ambiguous cases are routed to review |
| Final node | Whether the graph reaches the expected terminal business response node before persistence |
| Safety behavior | Whether the workflow avoids unsupported refund execution |

Current eval scenarios:

- duplicate charge refund
- charge after cancellation
- refund outside allowed window
- high-value enterprise refund
- unclear or conflicting billing evidence
- missing customer record

---

## Demo / Screenshots / Example Outputs

Expected demo output should show a structured decision, for example:

```json
{
  "request_id": "DEMO-001",
  "customer_id": "cust_001",
  "refund_eligible": true,
  "refund_amount": 29.0,
  "risk_level": "medium",
  "needs_human_review": false,
  "decision_reason": "The mock billing record shows a duplicate charge and the retrieved refund policy allows refunds for confirmed duplicate charges.",
  "policy_basis": ["refund_policy.md#duplicate-charges"],
  "final_response": "You appear eligible for a refund for the duplicate charge. This decision is based on the refund policy and the billing evidence available in this demo system."
}
```

When LangSmith is configured, this section can later include screenshots of graph traces, node-level metadata, and evaluation runs.

---

## Reproducibility / Quickstart

From the monorepo root:

```zsh
cd projects/refund_decision_agent
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Copy environment variables:

```zsh
cp .env.example .env
```

Run demo:

```zsh
make demo
```

Run tests:

```zsh
make test
```

Run evals:

```zsh
make eval
```

Run policy retrieval demo:

```zsh
make run-policy-demo
```

Reset local decision history:

```zsh
make seed-data
```

Run full local verification:

```zsh
make check
```

Run API:

```zsh
make run-api
```

The default local mode is deterministic and does not require `OPENAI_API_KEY`.

---

## Repository Structure

```text
projects/refund_decision_agent/
├── app/
│   ├── __init__.py
│   ├── api.py
│   ├── config.py
│   ├── graph.py
│   ├── nodes.py
│   ├── state.py
│   ├── schemas.py
│   ├── tools.py
│   ├── policy_store.py
│   ├── decision_engine.py
│   ├── tracing.py
│   └── errors.py
├── data/
│   ├── policies/
│   ├── mock_billing_records.json
│   ├── mock_customers.json
│   └── decision_records.json
├── docs/
├── evals/
├── scripts/
│   ├── run_demo.py
│   ├── run_policy_demo.py
│   └── seed_data.py
├── tests/
├── .dockerignore
├── .env.example
├── Dockerfile
├── Makefile
├── README.md
└── requirements.txt
```

---

## What I Personally Built / Ownership

This is a portfolio learning project built as part of the broader `agentic-ai-systems-lab` monorepo.

The implemented scope includes:

- designing the refund decision graph workflow
- creating synthetic refund, cancellation, and billing policies
- implementing local policy retrieval
- implementing mock read-only billing/customer tools
- defining typed graph state and Pydantic schemas
- building deterministic risk routing and human-review flags
- adding evals, tests, API/demo commands, and observability hooks

All customer, policy, and billing data in this project is synthetic and used only for demonstration.

---

## Design Decisions and Tradeoffs

| Decision | Why | Tradeoff / Alternative |
|---|---|---|
| Local Markdown policy store for v1 | Keeps the RAG layer transparent and easy to inspect | A vector database would be more realistic for large corpora |
| Mock read-only billing tools | Demonstrates tool-using decision workflows safely | Real billing APIs would require credentials, auth, and compliance boundaries |
| No real refund execution | Prevents overclaiming and keeps the project safe | Future versions can add simulated approved-write execution |
| Deterministic routing after structured decision | Keeps workflow behavior testable and auditable | Pure agentic routing would be more flexible but less predictable |
| Human-review flag for high-value cases | Models enterprise risk control | Real approval systems would require identity, RBAC, and persistence |
| JSON decision records | Keeps persistence transparent, resettable, and GitHub-review friendly | SQLite would be stronger for concurrent or larger-scale storage |
| Cost-safe mock mode | Allows repeatable tests and CI without API cost | A live LLM extension can be added later behind isolated config |

---

## Limitations / Honest Scope

This project demonstrates a production-style pattern, not a production payment system.

Current boundaries:

- policies are synthetic local Markdown files
- billing and customer data are mocked
- retrieval is local and simple in v1
- no real refund is executed
- no real payment processor is connected
- persistence is append-only JSON, not a production datastore
- no production auth/RBAC is implemented
- no hosted production deployment is claimed
- LangSmith support depends on local environment configuration

Claim boundary:

```text
This project demonstrates policy-grounded refund decision orchestration, but it does not claim to automate real financial refunds.
```

---

## Future Improvements

Planned extensions:

- replace simple policy retrieval with embedding-based retrieval
- add larger synthetic policy corpus and contradiction cases
- add simulated approved-write refund execution with idempotency
- add SQLite-backed decision and review persistence
- add durable checkpointing for human-review workflows
- add stronger RAG evaluation for retrieval accuracy and groundedness
- add LangSmith trace screenshots and evaluation examples
- add Docker and GitHub Actions CI once the v1 workflow stabilizes
- add authentication and RBAC design notes for production extension

---

## Skills Demonstrated

### Agentic AI / Workflow Systems

- LangGraph workflow design
- typed graph state
- structured refund decision outputs
- deterministic routing around structured decisions
- human-review routing for high-risk cases

### RAG / Policy-Grounded AI

- local policy retrieval
- policy-grounded decision context
- separation of policy knowledge from billing evidence
- grounded response generation

### Tool Safety / Guardrails

- read-only mock tools
- no-write-action v1 boundary
- high-value refund review gates
- safe handling of ambiguous or missing evidence

### Backend / Systems Engineering

- FastAPI service structure
- Pydantic request/response schemas
- Makefile-based local workflow
- Docker-ready repository structure
- testable module boundaries

### Evaluation / Observability

- local eval cases for refund decisions
- append-only JSON decision history
- workflow-path assertions
- structured trace events
- LangSmith-ready observability configuration
- cost-safe mock mode for repeatable testing
