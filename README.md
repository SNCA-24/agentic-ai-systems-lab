

# Agentic AI Systems Lab

A portfolio-focused monorepo for building production-style agentic AI systems.

This repository is designed as a hands-on lab for learning and demonstrating modern AI engineering patterns: graph-based orchestration, typed state, tool safety, human-in-the-loop workflows, evaluation, observability, API deployment, and production-oriented repo practices.

The goal is not to collect toy demos. The goal is to build progressively stronger, interview-ready, and portfolio-ready agentic AI projects.

---

## Current Project

### 1. Support Ticket Triage Agent v2

Location:

```text
projects/support_ticket_triage_agent_v2/
```

A LangGraph-based support ticket triage agent with:

- graph-based workflow orchestration
- typed state
- mock and LLM classifier modes
- deterministic routing
- risk-aware high-risk review path
- workflow path tracking
- structured trace events
- local evals
- pytest coverage
- LangSmith metadata
- FastAPI endpoints
- GitHub Actions CI
- API-level human approval flow
- in-memory approval decision store
- safe approval resume graph

Current verification status:

```text
pytest: 29/29 passed
local evals: 5/5 passed
CI: enabled
```

Project README:

```text
projects/support_ticket_triage_agent_v2/README.md
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
│   └── support_ticket_triage_agent_v2/
│       ├── app/
│       ├── evals/
│       ├── tests/
│       ├── README.md
│       └── requirements.txt
│
├── README.md
└── .gitignore
```

---

## Why This Repo Exists

Modern AI engineering is moving beyond single prompt-response apps.

Production-grade agentic systems need:

- explicit state management
- deterministic routing
- graph orchestration
- typed schemas
- structured outputs
- safe tool boundaries
- human approval gates
- observability and tracing
- local and CI-based evaluations
- API service layers
- cost-safe development modes
- clear deployment and debugging practices

This repo is a practical learning path for those skills.

---

## Core Engineering Principles

```text
LLMs should reason and classify.
Code should control workflow execution.
High-risk actions should require approval.
Tools should be typed and bounded.
State should be explicit and inspectable.
Every workflow should be testable.
Every important run should be traceable.
Local development should be cost-safe.
```

---

## Project 1: Support Ticket Triage Agent v2

### Architecture Summary

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
```

High-risk path:

```text
high-risk ticket
→ approval_status = pending
→ human approval decision recorded
→ approval decision can be retrieved
→ resume endpoint routes approved/rejected decisions safely
→ no real write action is executed yet
```

---

## Running Project 1 Locally

From the project folder:

```zsh
cd projects/support_ticket_triage_agent_v2
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Run local tests:

```zsh
pytest
```

Run local evals:

```zsh
python -m evals.run_eval
```

Run the FastAPI service:

```zsh
uvicorn app.api:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

---

## Cost-Safe Development

Project 1 supports a local mock classifier mode:

```text
CLASSIFIER_MODE=mock
```

This allows tests, evals, and API development without repeatedly calling an LLM provider.

LLM-backed classification is still supported through:

```text
CLASSIFIER_MODE=llm
```

---

## CI

This repository includes GitHub Actions CI for Project 1:

```text
.github/workflows/support-ticket-triage-ci.yml
```

The CI workflow runs:

```text
pytest
python -m evals.run_eval
```

CI uses cost-safe settings:

```text
CLASSIFIER_MODE=mock
APP_ENV=ci
LANGSMITH_TRACING=false
```

---

## Planned Project Ladder

This repo is intended to grow into a complete Agentic AI systems portfolio.

Planned projects:

1. **Support Ticket Triage Agent v2** — graph routing, HITL foundation, FastAPI, evals, tracing
2. **Refund Decision Agent** — RAG + policy grounding + billing tools
3. **Human Approval Action Agent** — durable checkpointing, approval gates, idempotent write tools
4. **Multi-Agent Incident Investigator** — supervisor-worker orchestration across simulated systems
5. **Enterprise AgentOps Workflow System** — tracing, eval dashboards, deployment, monitoring, and regression testing

---

## Skills Demonstrated

This repo is designed to demonstrate skills relevant to AI Engineer, Agentic AI Engineer, and LLM Engineer roles:

- LangGraph orchestration
- graph-based workflow design
- typed agent state
- structured classifier outputs
- deterministic routing
- human-in-the-loop workflow design
- approval safety patterns
- FastAPI service design
- local evaluation design
- pytest-based test coverage
- LangSmith observability metadata
- CI/CD basics for agent systems
- cost-aware local development
- production-style repository hygiene

---

## Current Status

```text
Project 1: Support Ticket Triage Agent v2
Status: active / portfolio-ready baseline
Tests: 29/29 passing
Evals: 5/5 passing
CI: enabled
Next major milestone: durable LangGraph checkpoint/resume for HITL workflows
```

---

## Author Notes

This lab is being built incrementally to mirror how production AI systems are actually engineered: small safe changes, tests first where possible, explicit state, observable workflows, and clear separation between prototype behavior and production-ready behavior.