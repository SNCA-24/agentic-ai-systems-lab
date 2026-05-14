# Support Ticket Triage Agent v2

A production-style graph-orchestrated AI agent for support ticket triage.

This project demonstrates how to design an enterprise-style agent workflow using explicit state, graph-based routing, structured classification, risk-aware handling, trace events, local evaluations, FastAPI service endpoints, and LangSmith observability metadata.

The goal is not to build a toy chatbot. The goal is to show how an AI agent can be engineered as a controlled workflow where the LLM classifies, deterministic code routes, high-risk requests are isolated, and every run can be evaluated and traced.

---

## Current Status

Implemented:

- LangGraph-based workflow
- Typed graph state using `TypedDict`
- Mock classifier mode for cost-safe local development
- LLM structured-output classifier path using OpenAI
- Deterministic routing after classification
- Risk-aware high-risk review path
- Workflow path tracking
- Structured trace events
- Local evaluation runner
- LangSmith metadata and tags for demo/eval/API runs
- FastAPI service layer with `/health`, `/tickets/triage`, and `/tickets/{ticket_id}/approval`
- API tests using FastAPI `TestClient`
- GitHub monorepo integration
- GitHub Actions CI for pytest and local evals

Current eval/test status:

```text
Passed 5/5 evals
pytest: 18/18 passed
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
- observability
- evaluation
- reproducible local runs
- cost-safe development mode

This project implements those ideas in a small but realistic support-ticket triage use case.

---

## Architecture

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

The classifier produces structured fields such as:

```text
category
intent
risk_level
needs_human_review
confidence
decision_summary
```

The router then deterministically chooses the next node.

Important design rule:

```text
LLM classifies.
Code routes.
High-risk requests are isolated.
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
- workflow path
- trace events
- errors
- final response

This makes the workflow inspectable and testable.

---

### 2. Graph-Based Routing

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

### 4. Risk-Aware Handling

Normal tickets route to standard support paths.

Examples:

```text
Billing issue        → billing_node
Technical issue      → technical_node
General question     → general_node
High-risk request    → high_risk_review_node
```

High-risk examples:

- restore deleted users
- delete accounts
- grant admin access
- large refund requests
- security incidents
- data loss
- irreversible actions

High-risk requests are not executed automatically. They are routed to review.

---

### 5. Workflow Path Tracking

Each run stores the nodes visited:

```python
[
    "validate_input",
    "classify_ticket",
    "high_risk_review_node"
]
```

This allows evals to check whether the graph followed the expected path.

---

### 6. Trace Events

Each run also stores structured trace events.

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

This is a lightweight local observability layer before deeper production monitoring.

---

### 7. LangSmith Observability Metadata

The graph is invoked with LangSmith-friendly config metadata and tags for demo, eval, and API runs.

Tracked metadata includes:

- ticket ID
- classifier mode
- run source: `main`, `eval`, or `api`
- environment
- expected category
- expected risk level
- expected final node
- LangSmith project name

Useful tags include:

```text
support-ticket-triage
demo-run
eval-run
api-run
classifier:mock
env:local
```

This makes runs easier to filter and inspect in LangSmith.

---

## Project Structure

```text
support_ticket_triage_agent_v2/
├── app/
│   ├── __init__.py
│   ├── api.py
│   ├── config.py
│   ├── graph.py
│   ├── nodes.py
│   ├── schemas.py
│   └── state.py
│
├── evals/
│   ├── __init__.py
│   ├── run_eval.py
│   └── test_cases.json
│
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_mock_classifier.py
│   ├── test_routing.py
│   └── test_trace_events.py
│
├── .env.example
├── .gitignore
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
- FastAPI health check
- FastAPI triage endpoint behavior
- FastAPI approval endpoint behavior

Current expected result:

```text
18 passed
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

Submit a ticket for triage:

```zsh
curl -X POST http://127.0.0.1:8000/tickets/triage \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": "123", "user_message": "My app crashes on upload."}'
```

Record a human approval decision:

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
  "message": "Approval recorded. Workflow resume is not implemented yet."
}
```

Important: this approval endpoint records a typed approval decision only. Durable graph resume and checkpointing are planned for a later step.

View interactive API docs at:

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

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

Expected route:

```text
validate_input → classify_ticket → high_risk_review_node
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
Route high-risk requests to review.
Run local evals in mock mode to control cost.
Attach LangSmith metadata for observability.
Use FastAPI for service endpoints.
```

---

## What This Project Is Not Yet

This version does not yet include:

- real billing tools
- real CRM tools
- RAG over policy documents
- durable human approval interrupts and graph resume
- persistent checkpointing
- FastAPI deployment beyond local dev
- production auth/security
- LangSmith dataset-based experiments

These are planned future extensions.

---

## Planned Next Steps

1. Add durable human-in-the-loop approval resume with checkpointing
2. Add RAG over refund/support policy documents
3. Add tool design layer with read/write tool separation
4. Add persistent checkpointing
5. Add LangSmith dataset-based evaluation
6. Add Dockerfile and deployment guide
7. Add deployment notes for running the FastAPI service

---

## Resume Bullet

Built a LangGraph-based support ticket triage agent with typed state, structured classification, deterministic routing, risk-aware high-risk review, workflow-path tracking, trace events, local evals, pytest coverage, FastAPI service endpoints, cost-safe mock mode, and LangSmith observability metadata.

---

## Portfolio Positioning

This project demonstrates practical agent engineering skills relevant to AI Engineer, Agentic AI Engineer, and LLM Engineer roles:

- graph orchestration
- stateful agent design
- typed schemas
- structured outputs
- safe routing
- risk-aware workflows
- observability
- evaluation
- cost-aware development
- production-oriented architecture