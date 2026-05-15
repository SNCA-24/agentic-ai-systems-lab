# Support Ticket Triage Agent v2

A production-style graph-orchestrated AI agent for support ticket triage.

This project demonstrates how to design an enterprise-style agent workflow using explicit state, graph-based routing, structured classification, risk-aware handling, typed tools, human-in-the-loop approval, idempotency, SQLite-backed persistence, checkpointed graph execution, interrupt-style pause/resume, FastAPI endpoints, local evaluations, and LangSmith observability metadata.

The goal is not to build a toy chatbot. The goal is to show how an AI agent can be engineered as a controlled workflow where the LLM classifies, deterministic code routes, high-risk requests are isolated, approvals are explicit, write actions are idempotency-protected, and every run can be evaluated and traced.

---

## Current Status

Implemented:

- LangGraph-based workflow
- Typed graph state using `TypedDict`
- Mock classifier mode for cost-safe local development
- LLM structured-output classifier path using OpenAI
- Deterministic routing after classification
- Risk-aware high-risk review path
- Human-in-the-loop approval flow
- Approved simulated write-tool execution
- Idempotency-protected action execution
- SQLite-backed approval and action execution persistence
- Checkpointed graph variants with `thread_id`
- True interrupt-style HITL graph experiment using `interrupt()` and `Command(resume=...)`
- Workflow path tracking
- Structured trace events
- Simulated read-only, preview-only, and approved-write tool layers
- Tool result capture in graph state via `tool_results`
- Local evaluation runner
- LangSmith metadata and tags for demo/eval/API/checkpointed runs
- FastAPI service layer with standard and checkpointed endpoints
- API tests using FastAPI `TestClient`
- GitHub monorepo integration
- GitHub Actions CI for pytest and local evals
- Architecture documentation in `docs/architecture.md`
- Demo scripts for interruptible graph and checkpointed API flows
- Project-level `Makefile` for common local commands
- Dockerfile for local containerized FastAPI runs

Current eval/test status:

```text
Passed 5/5 evals
pytest: 70/70 passed
```

---

## Why This Project Exists

Most simple agent demos look like this:

```text
User message → LLM → Tool call → Final answer
```

That is not enough for production systems.

Production agent workflows need:

- explicit state
- deterministic routing
- typed schemas
- safe handling of high-risk requests
- human approval gates
- read/write tool boundaries
- idempotency for write actions
- persistent approval/action records
- checkpointed workflow execution
- observability
- evaluation
- reproducible local runs
- cost-safe development mode

This project implements those ideas in a small but realistic support-ticket triage use case.

---

## Milestone Summary

### Milestone A — Approved Simulated Write-Tool Execution

Milestone A added the approved action execution path.

```text
approval recorded
→ resume safely
→ execute approved simulated write tool
→ store action execution record
→ prevent duplicate execution with idempotency
```

Key additions:

- `app/write_tools.py`
- `app/action_store.py` as the original JSON-backed reference store
- `data/action_executions.json` as the original JSON-backed action execution store
- `execute_approved_action_node`
- `execute_approved_high_risk_action`
- idempotency key generation
- API-level idempotency tests

Approved resume path:

```text
approval_resume_entry_node
→ approval_approved_node
→ execute_approved_action_node
→ END
```

Rejected resume path:

```text
approval_resume_entry_node
→ approval_rejected_node
→ END
```

Repeated approved resume calls are idempotency-protected:

```text
first resume  → write simulation executes
second resume → duplicate execution is skipped
```

---

### Milestone B — SQLite-Backed Persistence

Milestone B replaced the active runtime persistence layer with SQLite.

Active runtime database:

```text
data/support_agent.db
```

The database is generated automatically and ignored by Git.

Current SQLite tables:

```text
approval_records
action_execution_records
```

Key additions:

- `app/db.py`
- `app/sqlite_approval_store.py`
- `app/sqlite_action_store.py`
- `tests/test_sqlite_approval_store.py`
- `tests/test_sqlite_action_store.py`

Runtime persistence behavior:

```text
approval decisions       → SQLite approval_records
action execution records → SQLite action_execution_records
```

The earlier JSON-backed stores remain as simple reference implementations:

```text
app/approval_store.py
app/action_store.py
data/approvals.json
data/action_executions.json
```

They are no longer the active runtime persistence layer.

---

### Milestone C — Checkpointing and True Interrupt-Style HITL

Milestone C added checkpointing, checkpointed API endpoints, and a true interrupt-style HITL graph experiment.

#### C.1 — Checkpointing helpers

Added:

- `app/checkpointing.py`
- `create_memory_checkpointer()`
- `build_thread_id(ticket_id)`
- `build_graph_config(thread_id)`

Thread ID format:

```text
support-ticket:<ticket_id>
```

#### C.2 — Checkpointed graph variants and API endpoints

Added graph variants:

```text
checkpointed_ticket_graph
checkpointed_approval_resume_graph
```

Added API endpoints:

```text
POST /tickets/triage/checkpointed
POST /tickets/{ticket_id}/resume/checkpointed
```

These expose `thread_id` in API responses and run through checkpoint-enabled graph variants.

#### C.3 — True interrupt-style HITL experiment

Added:

```text
interruptible_ticket_graph
human_approval_interrupt_node
```

The interruptible graph uses:

```python
from langgraph.types import interrupt, Command
```

High-risk interruptible flow:

```text
validate_input
→ classify_ticket
→ high_risk_review_node
→ human_approval_interrupt_node
→ interrupt(...)
```

Approved resume:

```text
Command(resume={"approved": true, ...})
→ human_approval_interrupt_node
→ approval_approved_node
→ execute_approved_action_node
→ END
```

Rejected resume:

```text
Command(resume={"approved": false, ...})
→ human_approval_interrupt_node
→ approval_rejected_node
→ END
```

This demonstrates the real graph pause/resume pattern while keeping the public API stable.

---

## Architecture

### Standard triage graph

```text
User ticket
   ↓
validate_input
   ↓
classify_ticket
   ↓
route_after_classification
   ├── billing_node
   ├── technical_node
   ├── general_node
   └── high_risk_review_node
   ↓
END
```

### Approval resume graph

```text
approval_resume_entry_node
   ├── approval_approved_node
   │      ↓
   │   execute_approved_action_node
   │      ↓
   │     END
   ├── approval_rejected_node → END
   └── approval_blocked_node  → END
```

### Interruptible HITL graph experiment

```text
validate_input
→ classify_ticket
→ high_risk_review_node
→ human_approval_interrupt_node
→ interrupt(...)
→ Command(resume={...})
→ approval_approved_node / approval_rejected_node
→ execute_approved_action_node if approved
```

Important design rule:

```text
LLM classifies.
Code routes.
High-risk requests are isolated.
Approval changes authorization state.
Write execution is simulated, typed, persisted, and idempotency-protected.
```

---

## Human-in-the-Loop Design

High-risk requests follow a staged HITL flow.

Stable API-level flow:

```text
1. POST /tickets/triage
   → high-risk ticket routes to high_risk_review_node
   → preview_high_risk_action generates a preview-only action review
   → approval_status = pending
   → no write action is executed

2. POST /tickets/{ticket_id}/approval
   → records approved/rejected decision in SQLite

3. GET /tickets/{ticket_id}/approval
   → retrieves latest approval decision from SQLite

4. POST /tickets/{ticket_id}/resume
   → approved decisions execute approved simulated write tool once
   → repeated approved resume is idempotency-protected
   → rejected decisions are blocked
```

Checkpointed API flow:

```text
POST /tickets/triage/checkpointed
→ runs checkpointed_ticket_graph
→ returns thread_id

POST /tickets/{ticket_id}/resume/checkpointed
→ runs checkpointed_approval_resume_graph
→ returns thread_id and last_tool_result
```

Interruptible graph experiment:

```text
interruptible_ticket_graph.invoke(initial_state, config={"configurable": {"thread_id": ...}})
→ high-risk ticket pauses at interrupt(...)

interruptible_ticket_graph.invoke(Command(resume={...}), config=same_config)
→ same graph thread resumes
→ approved path executes simulated write tool
→ rejected path blocks safely
```

For deeper design details, see:

```text
docs/hitl_design.md
```

For system architecture diagrams, see:

```text
docs/architecture.md
```

---

## Core Concepts Demonstrated

### 1. Explicit State

The graph uses a shared state object to track:

- ticket ID
- user message
- category
- intent
- risk level
- human-review requirement
- confidence
- decision summary
- approval status
- approval ID
- reviewer notes
- workflow path
- trace events
- tool results
- errors
- final response

This makes the workflow inspectable and testable.

---

### 2. Deterministic Graph-Based Routing

Routing is handled by deterministic Python logic, not by free-form LLM decisions.

Example:

```python
if state["needs_human_review"] or state["risk_level"] == "high":
    return "high_risk"
```

This prevents the model from directly controlling high-risk workflow execution.

---

### 3. Cost-Safe Classifier Modes

The project supports two classifier modes:

```text
CLASSIFIER_MODE=mock  → local deterministic classifier
CLASSIFIER_MODE=llm   → OpenAI structured-output classifier
```

By default, the project uses:

```text
CLASSIFIER_MODE=mock
```

This allows repeated local development and eval runs without unnecessary OpenAI API usage.

---

### 4. Tool Layer and Tool Results

The project includes deterministic simulated tools that demonstrate safe enterprise tool design.

Pre-approval tools:

| Tool | Type | Used By | Purpose |
|---|---|---|---|
| `lookup_billing_record` | read-only | `billing_node` | Returns mock billing evidence for billing/duplicate-charge tickets |
| `get_technical_diagnostics` | read-only | `technical_node` | Returns mock diagnostics checklist for technical tickets |
| `preview_high_risk_action` | preview-only | `high_risk_review_node` | Generates a high-risk action preview without executing any write action |

Approved-action tool:

| Tool | Type | Used By | Purpose |
|---|---|---|---|
| `execute_approved_high_risk_action` | approved write simulation | `execute_approved_action_node` | Simulates approved high-risk action execution with idempotency protection |

Tool safety boundary:

```text
Read-only tools may run automatically.
Preview-only tools may run before approval.
Approved write simulations may run only after approval.
Real write tools are intentionally out of scope.
```

Tool outputs are captured in graph state as:

```text
tool_results
```

---

### 5. Idempotency

Approved write simulations are protected by idempotency keys.

Idempotency key format:

```text
<ticket_id>:<approval_id>:<action_type>
```

Example:

```text
HITL-001:approval_123:simulated_high_risk_action
```

Behavior:

```text
first approved resume  → simulated write action executes
second approved resume → duplicate execution is skipped
```

This demonstrates the production pattern used to avoid duplicate refunds, repeated account restores, repeated permission grants, or other duplicate side effects.

---

### 6. SQLite Persistence

Runtime persistence is SQLite-backed.

```text
data/support_agent.db
```

Tables:

| Table | Purpose |
|---|---|
| `approval_records` | Stores latest approval/rejection decision per ticket |
| `action_execution_records` | Stores idempotency-protected approved action execution records |

SQLite modules:

```text
app/sqlite_approval_store.py
app/sqlite_action_store.py
```

---

### 7. Checkpointing and Interrupts

Checkpoint helpers:

```text
app/checkpointing.py
```

Graph variants:

```text
checkpointed_ticket_graph
checkpointed_approval_resume_graph
interruptible_ticket_graph
```

The interruptible graph demonstrates:

```text
interrupt(...)
Command(resume={...})
same thread_id resume
approved path execution
rejected path blocking
```

---

### 8. Trace Events and Observability

Each run stores structured trace events.

Example:

```python
{
    "node": "classify_ticket",
    "event_type": "mock_classification_completed",
    "message": "Mock ticket classification completed.",
    "metadata": {
        "category": "technical",
        "risk_level": "high",
        "needs_human_review": True,
        "classifier_mode": "mock"
    }
}
```

The graph is invoked with LangSmith-friendly config metadata and tags for demo, eval, API, and checkpointed runs.

Useful tags include:

```text
support-ticket-triage
demo-run
eval-run
api-run
checkpointed-api-run
checkpointed-resume-run
classifier:mock
env:local
```

---

## Project Structure

```text
support_ticket_triage_agent_v2/
├── app/
│   ├── __init__.py
│   ├── action_store.py
│   ├── api.py
│   ├── checkpointing.py
│   ├── config.py
│   ├── db.py
│   ├── graph.py
│   ├── nodes.py
│   ├── schemas.py
│   ├── sqlite_action_store.py
│   ├── sqlite_approval_store.py
│   ├── state.py
│   ├── tools.py
│   └── write_tools.py
│
├── data/
│   ├── action_executions.json
│   └── approvals.json
│   # support_agent.db is generated locally and ignored by Git
│
├── docs/
│   ├── architecture.md
│   └── hitl_design.md
│
├── evals/
│   ├── __init__.py
│   ├── run_eval.py
│   └── test_cases.json
│
├── scripts/
│   ├── demo_checkpointed_api.sh
│   └── demo_interruptible_graph.py
│
├── tests/
│   ├── __init__.py
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
│
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── Makefile
├── main.py
├── README.md
└── requirements.txt
```

---

## Setup

From this project folder:

```zsh
cd /Users/chaitu/Downloads/agentic_systems/agentic-ai-systems-lab/projects/support_ticket_triage_agent_v2
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create a local `.env` file:

```zsh
cp .env.example .env
```

Example `.env`:

```text
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
CLASSIFIER_MODE=mock

APP_ENV=local
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=support-ticket-triage-agent-v2
LANGSMITH_RUN_TAG_PREFIX=support-ticket-triage
```

Do not commit `.env`.

---

## Running the Demo

Use mock mode for cost-safe local runs:

```zsh
python main.py
```

Expected behavior:

- technical tickets route to `technical_node`
- billing tickets route to `billing_node`
- general questions route to `general_node`
- high-risk tickets route to `high_risk_review_node`

---

## Makefile Commands

Common local commands are available through the project-level `Makefile`.

```zsh
make install          # install dependencies
make compile          # compile-check main app files and demo script
make test             # run pytest
make eval             # run local evals
make check            # run compile + tests + evals
make run-api          # run FastAPI with uvicorn
make demo-interrupt   # run interrupt-style graph demo
make demo-api         # run checkpointed API demo; requires API server running
make clean            # remove Python cache/test cache artifacts
```

Recommended verification command:

```zsh
make check
```

---

## Running Evaluations

```zsh
python -m evals.run_eval
```

The eval runner checks:

- category correctness
- risk-level correctness
- human-review requirement correctness
- final node correctness
- trace event recording

Current expected result:

```text
Passed 5/5 evals
```

---

## Demo Scripts

### Interruptible graph demo

This demonstrates the true LangGraph `interrupt()` / `Command(resume=...)` flow.

```zsh
python scripts/demo_interruptible_graph.py
```

Equivalent Makefile command:

```zsh
make demo-interrupt
```

Expected behavior:

```text
high-risk ticket
→ graph pauses with interrupt(...)
→ approval payload resumes same graph thread
→ approved simulated write tool executes
```

### Checkpointed API demo

Start the API in one terminal:

```zsh
make run-api
```

Then in another terminal:

```zsh
make demo-api
```

Expected behavior:

```text
checkpointed triage
→ approval recorded
→ first checkpointed resume executes approved write simulation
→ second checkpointed resume is skipped by idempotency
```

---

## Running Tests

```zsh
pytest
```

The test suite covers:

- mock classifier behavior
- graph routing behavior
- high-risk isolation
- empty input handling
- trace event recording
- simulated tool behavior
- read-only tool boundary
- preview-only high-risk action behavior
- approved simulated write-tool behavior
- idempotency behavior
- SQLite approval persistence
- SQLite action execution persistence
- FastAPI health check
- FastAPI triage endpoint behavior
- FastAPI approval endpoint behavior
- API-level approval resume behavior
- checkpointed API endpoints
- checkpointing helper utilities
- checkpointed graph variants
- true interrupt-style graph pause/resume

Current expected result:

```text
70 passed
```

---

## Continuous Integration

This project includes a GitHub Actions workflow at the repository root:

```text
.github/workflows/support-ticket-triage-ci.yml
```

The CI workflow runs on pushes and pull requests that affect this project. It uses cost-safe settings:

```text
CLASSIFIER_MODE=mock
APP_ENV=ci
LANGSMITH_TRACING=false
OPENAI_API_KEY=dummy-ci-key
```

CI steps:

```text
install dependencies
run pytest
run python -m evals.run_eval
```

This keeps the project automatically verifiable without calling OpenAI or LangSmith during CI.

---

## Running the FastAPI Service

Run the FastAPI development server with:

```zsh
uvicorn app.api:app --reload
```

Check health endpoint:

```zsh
curl http://127.0.0.1:8000/health
```

Example response:

```json
{
  "status": "ok",
  "classifier_mode": "mock",
  "environment": "local"
}
```

---

### Standard Triage

```zsh
curl -X POST http://127.0.0.1:8000/tickets/triage \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": "CURL-001", "user_message": "I was charged twice for my subscription."}'
```

---

### Checkpointed Triage

```zsh
curl -X POST http://127.0.0.1:8000/tickets/triage/checkpointed \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": "CURL-CKPT-001", "user_message": "I was charged twice for my subscription."}'
```

Expected key field:

```json
{
  "thread_id": "support-ticket:CURL-CKPT-001"
}
```

---

### Record Human Approval

```zsh
curl -X POST http://127.0.0.1:8000/tickets/CURL-002/approval \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "approval_id": "approval_123", "approved_by": "manager_001", "approval_notes": "Requester verified and action approved."}'
```

Expected key fields:

```json
{
  "ticket_id": "CURL-002",
  "approval_status": "approved",
  "approval_id": "approval_123",
  "approved_by": "manager_001",
  "message": "Approval recorded. Workflow can now be resumed safely."
}
```

Approvals are stored in SQLite:

```text
data/support_agent.db → approval_records
```

---

### Retrieve Approval

```zsh
curl http://127.0.0.1:8000/tickets/CURL-002/approval
```

---

### Standard Resume

```zsh
curl -X POST http://127.0.0.1:8000/tickets/CURL-002/resume
```

Expected approved workflow path:

```json
{
  "workflow_path": [
    "approval_resume_entry_node",
    "approval_approved_node",
    "execute_approved_action_node"
  ],
  "tool_results_count": 1
}
```

Repeated resume calls with the same approval are idempotency-protected.

---

### Checkpointed Resume

```zsh
curl -X POST http://127.0.0.1:8000/tickets/CURL-002/resume/checkpointed
```

Expected key fields:

```json
{
  "thread_id": "support-ticket:CURL-002",
  "workflow_path": [
    "approval_resume_entry_node",
    "approval_approved_node",
    "execute_approved_action_node"
  ],
  "tool_results_count": 1
}
```

---

### Swagger UI

View interactive API docs at:

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Docker Run

Build the local Docker image from the project folder:

```zsh
docker build -t support-ticket-triage-agent-v2 .
```

Run the container on port `8001` to avoid conflicts with any local `uvicorn` process on port `8000`:

```zsh
docker run --rm -p 8001:8000 \
  -e CLASSIFIER_MODE=mock \
  -e APP_ENV=docker \
  -e LANGSMITH_TRACING=false \
  -e OPENAI_API_KEY=dummy-docker-key \
  support-ticket-triage-agent-v2
```

Verify from another terminal:

```zsh
curl http://127.0.0.1:8001/health
```

Expected response:

```json
{
  "status": "ok",
  "classifier_mode": "mock",
  "environment": "docker"
}
```

---

## Example Tickets

### Technical Ticket

```text
My app keeps crashing whenever I upload a PDF.
```

Expected route:

```text
validate_input → classify_ticket → technical_node
```

---

### Billing Ticket

```text
I was charged twice for my subscription.
```

Expected route:

```text
validate_input → classify_ticket → billing_node
```

---

### High-Risk Ticket

```text
Our admin deleted 80 users. Can you restore them immediately?
```

Expected standard route:

```text
validate_input → classify_ticket → high_risk_review_node
```

Expected interruptible route:

```text
validate_input
→ classify_ticket
→ high_risk_review_node
→ human_approval_interrupt_node
→ interrupt(...)
```

---

## Design Principles

This project follows these production-agent principles:

```text
Use deterministic routing for control flow.
Use LLMs for classification and language understanding.
Use typed state for inspectability.
Track workflow paths for evaluation.
Track trace events for debugging.
Capture tool results as structured state.
Route high-risk requests to review.
Use read-only tools for automatic evidence collection.
Use preview-only tools for high-risk action review.
Require approval before approved write simulations.
Protect write execution with idempotency.
Persist approvals and action execution records in SQLite.
Use checkpointed graphs with thread_id.
Use interrupt()/Command(resume=...) for true HITL graph experiments.
Run local evals in mock mode to control cost.
Attach LangSmith metadata for observability.
Use FastAPI for service endpoints.
```

---

## What This Project Is Not Yet

This version does not yet include:

- real billing tools beyond deterministic simulations
- real CRM/admin tools beyond deterministic simulations
- RAG over policy documents
- durable checkpointing beyond local `MemorySaver`
- Postgres-backed production persistence
- production auth/security
- approver identity verification
- role-based approval authorization
- LangSmith dataset-based experiments
- hosted FastAPI deployment beyond local Docker/dev runs

These are future extensions, not blockers for the current portfolio milestone.

---

## Planned Next Steps

Project 1 core engineering milestones are complete. Remaining work is final polish:

1. Add LangSmith screenshots or run-inspection notes
2. Add final cleanup checklist before starting Project 2
3. Optionally add a short demo GIF or terminal-output screenshot
4. Optionally add production extension notes for Postgres, durable checkpointing, auth, and real tools

---

## Resume Bullet

Built a LangGraph-based support ticket triage agent with typed state, structured classification, deterministic routing, risk-aware high-risk review, trace events, simulated read-only/preview-only tools, approved write-tool simulation, idempotency protection, SQLite-backed persistence, checkpointed graph variants, interrupt-style HITL pause/resume with `Command(resume=...)`, local evals, pytest coverage, FastAPI endpoints, cost-safe mock mode, and LangSmith observability metadata.

---

## Portfolio Positioning

This project demonstrates practical agent engineering skills relevant to AI Engineer, Agentic AI Engineer, and LLM Engineer roles:

- graph orchestration
- stateful agent design
- typed schemas
- structured outputs
- deterministic routing
- safe routing
- read-only vs preview-only vs approved-write tool design
- tool-result state capture
- risk-aware workflows
- human-in-the-loop approval gates
- idempotency for write actions
- SQLite-backed persistence
- checkpointed graph execution
- interrupt-style HITL pause/resume
- observability
- evaluation
- cost-aware development
- production-oriented architecture