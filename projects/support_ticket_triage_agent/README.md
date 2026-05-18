# Support Ticket Triage Agent

A production-style agent workflow for support ticket triage that combines LangGraph orchestration, deterministic routing, human approval gates, idempotent simulated write actions, and a FastAPI service layer.

## Tech Stack Snapshot

- **AI / Agent workflow:** LangGraph, OpenAI structured outputs, LangSmith metadata/tags
- **Backend / API:** Python, FastAPI, Uvicorn, Pydantic
- **Persistence / state:** SQLite, TypedDict-based graph state, in-memory LangGraph checkpointing
- **Engineering:** pytest, Makefile, Docker, demo scripts

## Why This Project Exists

Many agent demos stop at `prompt -> tool call -> answer`. That is not enough for workflows where support requests can trigger high-risk account, permission, security, or financial actions.

This project exists to show a safer pattern:

- let the model classify into a strict schema
- keep routing and authorization in deterministic code
- require human approval before any high-risk write path
- record approval and action state for auditability
- make repeated resume calls safe with idempotency

The scope is intentionally local and conservative. The project demonstrates the workflow pattern, not a deployed production support platform.

## What This Project Builds

This project builds:

- a LangGraph ticket-triage workflow with explicit typed state
- a FastAPI service with triage, approval, resume, and checkpointed endpoints
- a simulated tool layer with read-only, preview-only, and approved-write boundaries
- a SQLite-backed approval store and action execution store
- a checkpointed graph path plus a true interrupt-style HITL graph experiment
- local evals, API tests, graph tests, persistence tests, and demo scripts

Out of scope:

- real external write tools
- production authentication or RBAC
- durable checkpoint storage beyond local `MemorySaver`
- hosted deployment or multi-worker coordination

## Architecture / Workflow

### End-to-end flow

```text
User ticket
-> validate_input
-> classify_ticket
-> deterministic route
   -> billing_node
   -> technical_node
   -> general_node
   -> high_risk_review_node

High-risk path
-> preview_high_risk_action
-> approval_status = pending
-> record approval in SQLite
-> resume workflow
-> execute approved simulated write action once
```

### Graph variants

| Graph | Purpose |
|---|---|
| `ticket_graph` | Standard triage flow |
| `approval_resume_graph` | Safe resume after approval lookup |
| `checkpointed_ticket_graph` | Triage flow with `thread_id` config |
| `checkpointed_approval_resume_graph` | Resume flow with `thread_id` config |
| `interruptible_ticket_graph` | True `interrupt()` / `Command(resume=...)` experiment |

### Major runtime components

| Component | Role |
|---|---|
| `app/api.py` | FastAPI endpoints and LangSmith-friendly run metadata |
| `app/graph.py` | Graph assembly and route wiring |
| `app/nodes.py` | Validation, classification, routing, approval, interrupt, execution nodes |
| `app/tools.py` | Read-only and preview-only simulated tools |
| `app/write_tools.py` | Approved simulated write tool with idempotency |
| `app/db.py` | SQLite initialization |
| `app/sqlite_approval_store.py` | Approval persistence |
| `app/sqlite_action_store.py` | Action execution persistence |
| `app/checkpointing.py` | `MemorySaver`, `thread_id`, graph config helpers |

## Key Features

### Agent workflow

- Explicit graph state using `TypedDict`
- Mock classifier mode for cost-safe local runs
- OpenAI structured-output classifier path for LLM-backed classification
- Deterministic routing that keeps control flow out of free-form model output
- Workflow path tracking and structured trace events

### Safety and approval

- High-risk requests route to human review
- Preview-only action review before approval
- Approval record and approval lookup endpoints
- Approved write simulation only after an explicit approval decision
- Idempotency keys prevent duplicate approved action execution

### Engineering and reproducibility

- FastAPI endpoints for standard and checkpointed flows
- SQLite-backed local persistence
- Local eval runner with scenario-based checks
- pytest coverage across API, routing, tools, persistence, checkpointing, and interrupt flows
- Dockerfile, Makefile, and shell/Python demos for repeatable local runs

## Technical Implementation

### Execution flow

`validate_input` normalizes and rejects empty tickets. `classify_ticket` then uses either a deterministic mock classifier or the OpenAI structured-output path to assign `category`, `intent`, `risk_level`, `needs_human_review`, `confidence`, and `decision_summary`.

`route_after_classification` sends the workflow to one of four main nodes:

- `billing_node` runs `lookup_billing_record`
- `technical_node` runs `get_technical_diagnostics`
- `general_node` returns a direct support response
- `high_risk_review_node` runs `preview_high_risk_action` and marks the workflow as `pending`

Resume flows load the latest approval from SQLite and branch to:

- `approval_approved_node` -> `execute_approved_action_node`
- `approval_rejected_node`
- `approval_blocked_node`

The approved execution node builds an idempotency key in the format `<ticket_id>:<approval_id>:<action_type>` and stores the execution result in SQLite.

### API surface

| Endpoint | Purpose |
|---|---|
| `GET /health` | Health check and active classifier mode |
| `POST /tickets/triage` | Standard ticket triage |
| `POST /tickets/triage/checkpointed` | Triage through checkpoint-enabled graph |
| `POST /tickets/{ticket_id}/approval` | Record approval or rejection |
| `GET /tickets/{ticket_id}/approval` | Fetch latest approval decision |
| `POST /tickets/{ticket_id}/resume` | Resume high-risk workflow |
| `POST /tickets/{ticket_id}/resume/checkpointed` | Resume through checkpoint-enabled graph |

### Outputs / artifacts

- `data/support_agent.db`: generated local SQLite database
- `data/approvals.json`: legacy/reference JSON approval store
- `data/action_executions.json`: legacy/reference JSON action store
- `tool_results`, `workflow_path`, and `trace_events` in graph state

### State and tool boundaries

The shared graph state tracks:

- ticket identity and raw user message
- classification outputs such as `category`, `intent`, `risk_level`, and `confidence`
- approval fields such as `approval_status`, `approval_id`, `approval_notes`, and `approved_by`
- workflow observability fields such as `workflow_path`, `trace_events`, and `tool_results`
- terminal outputs such as `errors` and `final_response`

The tool layer is deliberately split by risk:

| Tool | Type | Used by | Purpose |
|---|---|---|---|
| `lookup_billing_record` | read-only | `billing_node` | Returns mock billing evidence for billing or duplicate-charge tickets |
| `get_technical_diagnostics` | read-only | `technical_node` | Returns a deterministic diagnostics checklist for technical tickets |
| `preview_high_risk_action` | preview-only | `high_risk_review_node` | Produces a review artifact without executing a write action |
| `execute_approved_high_risk_action` | approved write simulation | `execute_approved_action_node` | Simulates a high-risk action once approval exists and idempotency allows it |

Safety boundary:

```text
read-only tools may run automatically
preview-only tools may run before approval
approved write simulations may run only after approval
real external write tools are intentionally out of scope
```

## Data / Inputs / Assumptions

- Inputs are support ticket strings plus a caller-supplied `ticket_id`.
- Local eval cases are small synthetic scenarios stored in `evals/test_cases.json`.
- No external production dataset is committed to the repo.
- The SQLite database is generated locally and ignored by Git.
- The simulated tools return deterministic mock evidence and do not call external systems.
- `CLASSIFIER_MODE=mock` is the cost-safe default for local development and tests.
- `CLASSIFIER_MODE=llm` requires an OpenAI API key and uses the structured classification schema in `app/schemas.py`.

## Methodology / Guardrails

The core design choice is to split responsibilities deliberately:

- the model classifies into a strict schema
- deterministic Python decides route transitions
- high-risk requests are isolated before any write path
- pre-approval tools are read-only or preview-only
- approved actions are simulated and idempotency-protected

This keeps the project useful as an agent-systems example rather than a prompt-only demo.

## Evaluation / Results

### Fresh local verification

| Check | Result |
|---|---|
| `pytest -q` | 70 passed |
| `python -m evals.run_eval` | 5/5 passed |

### What those checks cover

- API routing and response shape
- approval recording and rejection handling
- idempotent approved resume behavior
- SQLite approval/action store round trips
- checkpoint helper behavior and checkpointed graph flows
- true interrupt-style graph pause/resume
- trace-event recording
- scenario-based eval coverage for billing, technical, general, and high-risk tickets

The project has good local correctness evidence for its current scope, but it does not include latency, throughput, or production reliability benchmarks.

The repo also includes a GitHub Actions workflow at `.github/workflows/support-ticket-triage-ci.yml` that targets `projects/support_ticket_triage_agent/**` and runs pytest plus local evals in `mock` mode with tracing disabled.

## Demo / Example Outputs

No screenshots are committed in the repo. The project does include runnable demos and API-oriented example outputs.

### `GET /health`

```json
{
  "status": "ok",
  "classifier_mode": "mock",
  "environment": "local"
}
```

### High-risk triage example

```json
{
  "ticket_id": "API-002",
  "category": "technical",
  "risk_level": "high",
  "needs_human_review": true,
  "approval_status": "pending",
  "workflow_path": [
    "validate_input",
    "classify_ticket",
    "high_risk_review_node"
  ]
}
```

### Idempotent resume behavior

```text
first resume  -> last_tool_result.status = success
second resume -> last_tool_result.status = skipped
```

### Example tickets

Technical ticket:

```text
My app keeps crashing whenever I upload a PDF.
```

Expected route:

```text
validate_input -> classify_ticket -> technical_node
```

Billing ticket:

```text
I was charged twice for my subscription.
```

Expected route:

```text
validate_input -> classify_ticket -> billing_node
```

High-risk ticket:

```text
Our admin deleted 80 users. Can you restore them immediately?
```

Expected standard route:

```text
validate_input -> classify_ticket -> high_risk_review_node
```

Expected interruptible route:

```text
validate_input
-> classify_ticket
-> high_risk_review_node
-> human_approval_interrupt_node
-> interrupt(...)
```

Demo entry points:

- `scripts/demo_interruptible_graph.py`
- `scripts/demo_checkpointed_api.sh`

## Reproducibility / Quickstart

### Local setup

```bash
cd projects/support_ticket_triage_agent
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Environment variables

Create a local `.env` from `.env.example` and set the values you need:

```bash
cp .env.example .env
```

Minimum notes:

- `CLASSIFIER_MODE=mock` works without live OpenAI calls
- `CLASSIFIER_MODE=llm` requires `OPENAI_API_KEY`
- LangSmith keys are optional unless you want live tracing

### Run the API

```bash
uvicorn app.api:app --reload
```

Open `http://127.0.0.1:8000/docs` for the local FastAPI docs.

### Run tests

```bash
pytest -q
```

### Run local evals

```bash
python -m evals.run_eval
```

### Run demos

```bash
python scripts/demo_interruptible_graph.py
zsh scripts/demo_checkpointed_api.sh
```

### Makefile shortcuts

```bash
make test
make eval
make check
make run-api
make demo-interrupt
make demo-api
```

### Docker

```bash
docker build -t support-ticket-triage-agent .
docker run --rm -p 8000:8000 \
  -e CLASSIFIER_MODE=mock \
  -e APP_ENV=docker \
  -e LANGSMITH_TRACING=false \
  -e OPENAI_API_KEY=dummy-docker-key \
  support-ticket-triage-agent
```

## Repository Structure

```text
projects/support_ticket_triage_agent/
├── app/
│   ├── api.py
│   ├── checkpointing.py
│   ├── db.py
│   ├── graph.py
│   ├── nodes.py
│   ├── schemas.py
│   ├── sqlite_action_store.py
│   ├── sqlite_approval_store.py
│   ├── state.py
│   ├── tools.py
│   └── write_tools.py
├── data/
│   ├── action_executions.json
│   └── approvals.json
├── docs/
│   ├── architecture.md
│   ├── final_cleanup_checklist.md
│   ├── github_readme_standard.md
│   └── hitl_design.md
├── evals/
│   ├── run_eval.py
│   └── test_cases.json
├── scripts/
│   ├── demo_checkpointed_api.sh
│   └── demo_interruptible_graph.py
├── tests/
│   ├── test_action_store.py
│   ├── test_api.py
│   ├── test_checkpointing.py
│   ├── test_interruptible_graph.py
│   ├── test_mock_classifier.py
│   ├── test_routing.py
│   ├── test_sqlite_action_store.py
│   ├── test_sqlite_approval_store.py
│   ├── test_tools.py
│   ├── test_trace_events.py
│   └── test_write_tools.py
├── Dockerfile
├── Makefile
├── README.md
├── main.py
└── requirements.txt
```

## What I Personally Built / Ownership

I implemented the current project surface in this folder, including:

- graph workflow design and node logic
- FastAPI endpoints and response schemas
- SQLite persistence and idempotency behavior
- checkpointing helpers and interrupt-style HITL experiment
- local eval runner and pytest suite
- docs, demo scripts, Dockerfile, and Makefile

The README does not claim live production deployment, real external tool integrations, or ownership of LangGraph/OpenAI/FastAPI dependencies. If collaboration or starter-code attribution becomes relevant later, it should be documented explicitly in this section.

## Design Decisions and Tradeoffs

| Decision | Why | Tradeoff / Alternative |
|---|---|---|
| LangGraph for orchestration | Makes workflow state, routes, and pause/resume behavior explicit | More structure than a simple prompt loop |
| Mock classifier mode by default | Keeps tests, evals, and local demos cheap and repeatable | Less realistic than always running live LLM classification |
| Deterministic routing after classification | Prevents the model from directly controlling high-risk execution paths | Requires more explicit code than an LLM-only router |
| SQLite for runtime persistence | Easy local setup with no external services | Not the right choice for multi-user or distributed production workloads |
| `MemorySaver` for checkpointing | Good local proof of `thread_id`-based resume behavior | Not durable across process restarts like a production checkpoint store |
| Simulated write tools | Demonstrates guardrail shape without real side effects | Does not prove integration with live billing/admin systems |
| Typed shared state | Makes route decisions, approvals, and trace artifacts inspectable in one place | More explicit bookkeeping than a lightweight prompt chain |
| Preview-only review before execution | Lets the workflow surface high-risk intent before side effects are allowed | Adds an extra step compared with an end-to-end autonomous agent |
| Scenario evals plus pytest | Covers both behavior assertions and end-to-end routing expectations | Limited benchmark depth compared with larger evaluation suites |
| Workflow docs and demos in-repo | Improves interview-readiness and reviewer comprehension | Adds maintenance cost when paths or names change |

## Limitations / Honest Scope

- This project uses simulated tools; it does not execute real external account, billing, or permission changes.
- Real billing, CRM, admin, and account tools are not implemented beyond deterministic simulations.
- Persistence is local SQLite, not a production database.
- Checkpointing uses local in-memory `MemorySaver`, not a durable checkpoint backend.
- Auth, RBAC, approval expiry, distributed locking, and multi-worker coordination are not implemented.
- RAG or policy-document grounding is not implemented in this version.
- No hosted deployment, production monitoring dashboard, or real user adoption evidence is included.
- If command wrappers fail after a local folder rename, recreate `.venv` so interpreter paths point to the current project folder.

Claim boundary:
This project demonstrates agent workflow design, HITL safety patterns, local persistence, checkpointing concepts, and reproducible local verification. It does not claim production deployment or live operational use.

## Future Improvements

- Add richer CI checks such as Docker build validation or demo-script smoke tests
- Replace `MemorySaver` with a durable checkpoint store
- Swap SQLite for Postgres plus migrations
- Add authentication and role-based approval controls
- Add approval expiration and richer audit metadata
- Introduce real external integrations behind the existing tool boundary
- Expand eval coverage with larger and more adversarial ticket sets
- Add deployment config and runtime observability beyond local metadata/tags

## Skills Demonstrated

### AI / Agent Systems

- LangGraph workflow orchestration
- structured LLM classification
- interrupt-style human-in-the-loop pause/resume
- safe tool boundary design
- agent state design and trace instrumentation

### Backend / Systems Engineering

- FastAPI endpoint design
- SQLite persistence
- idempotent action execution
- checkpoint configuration with stable `thread_id` values
- Dockerized local service setup

### Quality / Reliability

- pytest-based API and workflow testing
- scenario-based local evaluation
- reproducible local demos
- explicit limitations and production-boundary documentation

### Product / Workflow Thinking

- risk-aware ticket handling
- approval-gated high-risk operations
- audit-friendly workflow states and reviewer notes
- clear separation of model responsibility versus deterministic control
