# Agentic AI Systems Lab

A portfolio-focused monorepo for building production-style agentic AI systems with graph orchestration, human-in-the-loop workflows, tool safety, persistence, checkpointing, evaluation, observability, and API service layers.

This repository is organized as a growing lab of progressively stronger agentic AI projects. Each project is intended to be independently understandable, runnable, and portfolio-ready, while the monorepo shows the broader learning path across agent architecture patterns.

---

## Tech Stack Snapshot

- **Agent Orchestration:** LangGraph, typed graph state, checkpointing, interrupt/resume workflows
- **Backend / API:** Python, FastAPI, Uvicorn, Pydantic
- **Persistence:** SQLite, local JSON reference stores
- **Tooling / Safety:** read-only tools, preview-only tools, approved-write simulations, idempotency keys
- **Evaluation / Observability:** pytest, local eval runner, trace events, LangSmith metadata
- **Engineering:** Docker, Makefile, GitHub Actions, cost-safe mock mode

---

## Why This Monorepo Exists

Modern AI engineering is moving beyond simple prompt-response applications.

Production-style agentic systems need:

- explicit state management
- deterministic routing around LLM outputs
- graph-based workflow control
- typed schemas and structured outputs
- safe tool boundaries
- human approval gates
- idempotency for write actions
- persistent approval and execution records
- checkpointed workflow execution
- interrupt-style human-in-the-loop pause/resume
- local and CI-based evaluation
- observability and debugging hooks
- reproducible API/demo workflows
- cost-safe development modes

This monorepo is a practical portfolio lab for building those skills through concrete projects rather than isolated experiments.

---

## What This Repository Builds

This repository builds a sequence of agentic AI systems that increase in complexity over time.

Current and planned project themes include:

- graph-based support ticket triage
- refund decisioning with policy grounding
- human-approved action execution
- multi-agent incident investigation
- enterprise AgentOps workflows

The intended progression is:

```text
single graph agent
→ HITL approval workflow
→ RAG + policy-grounded decision agent
→ richer action approval systems
→ multi-agent orchestration
→ AgentOps / monitoring / evaluation layer
```

---

## Current Project Status

| Project | Status | Focus |
|---|---|---|
| Support Ticket Triage Agent | Complete / portfolio-ready foundation | Graph routing, HITL approval, simulated tools, idempotency, SQLite persistence, checkpointed graphs, interrupt-style pause/resume, FastAPI, evals |
| Refund Decision Agent | Complete / portfolio-ready foundation | RAG, policy grounding, mock billing evidence, deterministic refund decisions, JSON persistence, FastAPI, evals |
| Human Approval Action Agent | Planned next | richer approval policies, durable checkpointing, idempotent write-tool execution |
| Multi-Agent Incident Investigator | Planned | supervisor-worker orchestration across simulated systems |
| Enterprise AgentOps Workflow System | Planned | tracing, eval dashboards, deployment, monitoring, regression testing |

---

## Project 1 — Support Ticket Triage Agent

Location:

```text
projects/support_ticket_triage_agent/
```

Project-specific README:

```text
projects/support_ticket_triage_agent/README.md
```

For full implementation details, setup instructions, architecture diagrams, demo commands, tests, Docker usage, and design tradeoffs, refer to:

```text
projects/support_ticket_triage_agent/README.md
```

### One-Line Summary

A LangGraph-based support ticket triage agent that routes tickets through deterministic graph workflows, isolates high-risk requests, supports human approval, simulates approved write-tool execution with idempotency, persists approvals/actions in SQLite, and demonstrates checkpointed plus interrupt-style HITL flows.

### Current Verification

```text
pytest: 70/70 passed
local evals: 5/5 passed
GitHub Actions: enabled
```

### Project 1 Highlights

- typed graph state with explicit workflow tracking
- mock and LLM classifier modes
- deterministic routing after classification
- high-risk review path
- read-only, preview-only, and approved-write simulated tools
- approval-gated simulated write execution
- idempotency-protected action execution
- SQLite-backed approval and action execution persistence
- checkpointed graph variants with `thread_id`
- checkpointed FastAPI endpoints
- true interrupt-style HITL experiment with `interrupt()` and `Command(resume=...)`
- local eval runner and pytest coverage
- Docker, Makefile, and demo scripts
- GitHub Actions CI in cost-safe mock mode

### Project 1 High-Level Flow

```text
support ticket
→ validate input
→ classify ticket
→ deterministic route
→ standard support node OR high-risk review
→ preview-only action review for high-risk requests
→ approval decision
→ approved simulated write execution with idempotency
→ persisted audit-friendly result
```

For the detailed project-level README, use:

```text
projects/support_ticket_triage_agent/README.md
```

---

## Project 2 — Refund Decision Agent

Location:

```text
projects/refund_decision_agent/
```

Project-specific README:

```text
projects/refund_decision_agent/README.md
```

For full implementation details, setup instructions, architecture, demo commands, evals, tests, API usage, and design tradeoffs, refer to:

```text
projects/refund_decision_agent/README.md
```

### One-Line Summary

A LangGraph-based refund decision agent that retrieves synthetic refund/cancellation/billing policies, loads mock customer and billing evidence through read-only tools, applies deterministic refund eligibility logic, routes eligible/ineligible/review/escalation cases, persists JSON decision records, and exposes demo/eval/API workflows in cost-safe mock mode.

### Current Verification

```text
pytest: 66/66 passed
local evals: 6/6 passed
demo: 6/6 scenarios completed
policy demo: 3/3 retrieval scenarios completed
API tests: 13/13 passed
```

### Project 2 Highlights

- LangGraph workflow with typed refund decision state
- deterministic mock classification with approved refund-agent intent labels
- local Markdown policy retrieval over synthetic refund, cancellation, and billing policies
- mock read-only customer and billing evidence tools backed by JSON fixtures
- deterministic refund eligibility logic for duplicate charges, post-cancellation charges, refund windows, high-value refunds, enterprise cases, and conflicting evidence
- terminal routing across eligible, ineligible, human-review, and escalation paths
- append-only JSON decision persistence in `data/decision_records.json`
- workflow-path and trace-event observability
- FastAPI endpoint for refund decision requests
- local eval runner and pytest coverage
- demo and policy retrieval scripts
- cost-safe `CLASSIFIER_MODE=mock` default
- no real refund execution, no payment provider integration, and no real customer/payment data

### Project 2 High-Level Flow

```text
refund request
→ validate input
→ classify refund intent
→ retrieve relevant policy snippets
→ load mock customer and billing evidence
→ run deterministic eligibility logic
→ route to eligible, ineligible, human-review, or escalation response
→ persist JSON decision record
→ return grounded response
```

For the detailed project-level README, use:

```text
projects/refund_decision_agent/README.md
```

---

## Repository Structure

```text
agentic-ai-systems-lab/
├── .github/
│   └── workflows/
│       └── support-ticket-triage-ci.yml
│
├── projects/
│   ├── support_ticket_triage_agent/
│   │   ├── app/
│   │   ├── data/
│   │   ├── docs/
│   │   ├── evals/
│   │   ├── scripts/
│   │   ├── tests/
│   │   ├── .dockerignore
│   │   ├── .env.example
│   │   ├── Dockerfile
│   │   ├── Makefile
│   │   ├── README.md
│   │   └── requirements.txt
│   │
│   └── refund_decision_agent/
│       ├── app/
│       ├── data/
│       ├── docs/
│       ├── evals/
│       ├── scripts/
│       ├── tests/
│       ├── .dockerignore
│       ├── .env.example
│       ├── Dockerfile
│       ├── Makefile
│       ├── README.md
│       └── requirements.txt
│
├── README.md
└── .gitignore
```

---

## Quickstart for Completed Projects

### Project 1 — Support Ticket Triage Agent

From the repository root:

```zsh
cd projects/support_ticket_triage_agent
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Run tests:

```zsh
make test
```

Run evals:

```zsh
make eval
```

Run full local verification:

```zsh
make check
```

Run the API:

```zsh
make run-api
```

For complete usage, demos, Docker commands, and API examples, see:

```text
projects/support_ticket_triage_agent/README.md
```

### Project 2 — Refund Decision Agent

From the repository root:

```zsh
cd projects/refund_decision_agent
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Run tests:

```zsh
make test
```

Run evals:

```zsh
make eval
```

Run demo:

```zsh
make demo
```

Run full local verification:

```zsh
make check
```

Run the API:

```zsh
make run-api
```

For complete usage, demos, API examples, evals, and design tradeoffs, see:

```text
projects/refund_decision_agent/README.md
```

---

## Evaluation and CI

The completed projects include local verification checks. Project 1 also includes a GitHub Actions workflow.

Project 1 local verification:

```text
pytest: 70/70 passed
python -m evals.run_eval: 5/5 passed
```

Project 2 local verification:

```text
pytest: 66/66 passed
python -m evals.run_eval: 6/6 passed
scripts/run_demo.py: 6/6 scenarios completed
scripts/run_policy_demo.py: 3/3 retrieval scenarios completed
```

CI workflow:

```text
.github/workflows/support-ticket-triage-ci.yml
```

The workflow targets:

```text
projects/support_ticket_triage_agent/**
```

and runs in cost-safe mock mode:

```text
CLASSIFIER_MODE=mock
APP_ENV=ci
LANGSMITH_TRACING=false
OPENAI_API_KEY=dummy-ci-key
```

---

## Design Principles Across Projects

These principles guide every project in this monorepo:

```text
LLMs should reason and classify.
Code should control workflow execution.
State should be explicit and inspectable.
Tools should be typed, bounded, and separated by risk.
Read-only tools can collect evidence automatically.
Preview-only tools can support human review.
Approved write simulations require explicit approval and idempotency.
High-risk actions should require approval.
Persistence should make approval and execution records auditable.
Checkpointing should use stable thread IDs.
Interrupt-style workflows should pause safely and resume explicitly.
Every workflow should be testable.
Every important run should be traceable.
Local development should be cost-safe.
```

---

## Planned Project Ladder

### 1. Support Ticket Triage Agent — Complete

Focus:

```text
graph routing + HITL approval + simulated tools + idempotency + SQLite persistence + checkpointed graphs + interrupt-style pause/resume
```

Status:

```text
Complete / portfolio-ready foundation
```

Details:

```text
projects/support_ticket_triage_agent/README.md
```

---

### 2. Refund Decision Agent — Complete

Focus:

```text
RAG over synthetic refund, cancellation, and billing policies
policy-grounded refund decisioning
mock read-only customer and billing evidence tools
deterministic refund eligibility logic
structured refund decision output
escalation and human-review flags for high-value, enterprise, ambiguous, or conflicting cases
JSON decision persistence
evaluation over policy-grounded refund examples
FastAPI endpoint for refund decision requests
```

Learning objective:

```text
move from classification/routing agents to policy-grounded decision agents
```

Status:

```text
Complete / portfolio-ready foundation
```

Details:

```text
projects/refund_decision_agent/README.md
```

---

### 3. Human Approval Action Agent — Planned Next

Expected focus:

- richer approval policies
- approval expiration
- approver identity checks
- durable checkpointing beyond local memory
- idempotent write-tool execution patterns
- audit logs and action reconciliation

Likely learning objective:

```text
make HITL action execution closer to production-grade control systems
```

---

### 4. Multi-Agent Incident Investigator — Planned

Expected focus:

- supervisor-worker orchestration
- specialist agents for logs, metrics, tickets, and alerts
- evidence aggregation
- incident summarization
- escalation recommendations

Likely learning objective:

```text
learn when multi-agent patterns are useful and how to control them safely
```

---

### 5. Enterprise AgentOps Workflow System — Planned

Expected focus:

- evaluation dashboards
- tracing and observability workflows
- regression testing for agents
- deployment and monitoring notes
- failure analysis and replay

Likely learning objective:

```text
move from agent building to agent operations and reliability engineering
```

---

## Current Limitations and Scope

This monorepo is a portfolio and learning lab, not a production SaaS deployment.

Current boundaries:

- Project 1 uses simulated tools, not real CRM/billing/admin integrations
- Project 1 approved write execution is simulated only
- Project 1 SQLite persistence is local
- Project 1 checkpointing currently uses local/in-memory checkpointers where applicable
- Project 2 uses synthetic policies and mock customer/billing fixtures only
- Project 2 uses read-only evidence tools and does not execute real refunds
- Project 2 JSON decision persistence is local and demo-oriented
- no hosted production deployment is claimed
- no production auth/RBAC is implemented yet
- future projects after Project 2 are planned but not yet implemented

These boundaries are intentional and documented so the repository demonstrates engineering patterns without overclaiming production impact.

---

## Skills Demonstrated

### Agentic AI / LLM Systems

- graph-based orchestration
- typed agent state
- deterministic routing around model outputs
- structured classifier outputs
- HITL workflow design
- checkpointed graph execution
- interrupt-style pause/resume
- policy-grounded decision workflows
- RAG-backed agent state updates

### Tool Safety / Guardrails

- read-only tools
- preview-only tools
- approved-write simulations
- idempotency keys
- approval-gated execution
- safe handling of high-risk requests
- read-only evidence tools for refund decisioning
- human-review flags for high-value or ambiguous financial cases

### Backend / Systems Engineering

- FastAPI service design
- SQLite-backed local persistence
- Dockerized local API runs
- Makefile-based command interface
- GitHub Actions CI
- pytest-based coverage

### Evaluation / Observability

- local eval runner
- workflow-path assertions
- structured trace events
- LangSmith metadata/tags
- cost-safe mock mode for repeatable testing
- policy-grounded scenario evals
- workflow-path and final-node assertions across multiple graph agents

---

## Author Notes

This lab is being built incrementally to mirror how production AI systems are engineered: small safe changes, explicit state, deterministic control flow, approval gates, idempotency, persistence, checkpointing, evaluation, and clear separation between prototype behavior and production-ready behavior.
