# Agentic AI Systems Lab

A portfolio-focused monorepo for building production-style agentic AI systems.

This repository is designed as a hands-on lab for learning and demonstrating modern AI engineering patterns: graph-based orchestration, typed state, tool safety, human-in-the-loop workflows, idempotent write-tool execution, persistence, checkpointing, interrupt-style pause/resume, evaluation, observability, API service design, and production-oriented repo practices.

The goal is not to collect toy demos. The goal is to build progressively stronger, interview-ready, and portfolio-ready agentic AI projects that demonstrate how AI systems can be engineered with control, safety, traceability, and tests.

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
- simulated read-only, preview-only, and approved-write tool layers
- tool-result capture in graph state
- approved simulated write-tool execution
- idempotency-protected action execution
- SQLite-backed approval and action execution persistence
- checkpointed graph variants with `thread_id`
- checkpointed FastAPI endpoints
- true interrupt-style HITL graph experiment using `interrupt()` and `Command(resume=...)`
- local evals
- pytest coverage
- LangSmith metadata
- FastAPI endpoints
- GitHub Actions CI
- HITL design documentation

Current verification status:

```text
pytest: 70/70 passed
local evals: 5/5 passed
CI: enabled
```

Project README:

```text
projects/support_ticket_triage_agent_v2/README.md
```

Detailed HITL design:

```text
projects/support_ticket_triage_agent_v2/docs/hitl_design.md
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
│       │   ├── api.py
│       │   ├── checkpointing.py
│       │   ├── db.py
│       │   ├── graph.py
│       │   ├── nodes.py
│       │   ├── schemas.py
│       │   ├── sqlite_action_store.py
│       │   ├── sqlite_approval_store.py
│       │   ├── state.py
│       │   ├── tools.py
│       │   └── write_tools.py
│       ├── data/
│       │   ├── action_executions.json
│       │   └── approvals.json
│       │   # support_agent.db is generated locally and ignored by Git
│       ├── docs/
│       │   ├── architecture.md
│       │   └── hitl_design.md
│       ├── evals/
│       ├── scripts/
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
- idempotency for write actions
- persistent approval and action records
- checkpointed workflow execution
- interrupt-style human-in-the-loop pause/resume
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
Tools should be typed, bounded, and separated by risk.
Read-only tools can collect evidence automatically.
Preview-only tools can support human review.
Approved write simulations require explicit approval and idempotency.
State should be explicit and inspectable.
Persistence should make approval and execution records auditable.
Checkpointing should use stable thread IDs.
Interrupt-style workflows should pause safely and resume explicitly.
Every workflow should be testable.
Every important run should be traceable.
Local development should be cost-safe.
```

---

## Project 1: Support Ticket Triage Agent v2

### Architecture Summary

Standard triage graph:

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

Approval resume graph:

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

Interruptible HITL graph experiment:

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

---

## Project 1 Milestones Completed

### Milestone A — Approved Simulated Write-Tool Execution

Project 1 supports an approved action execution path:

```text
approval recorded
→ resume safely
→ execute approved simulated write tool
→ store action execution record
→ prevent duplicate execution with idempotency
```

Key behavior:

```text
first approved resume  → simulated write action executes
second approved resume → duplicate execution is skipped
rejected approval      → no write action executes
```

This demonstrates approval-gated write-tool safety and idempotency.

---

### Milestone B — SQLite-Backed Persistence

Project 1 uses SQLite-backed runtime persistence:

```text
data/support_agent.db
```

Runtime tables:

```text
approval_records
action_execution_records
```

Current behavior:

```text
approval decisions       → SQLite approval_records
action execution records → SQLite action_execution_records
```

The earlier JSON-backed stores remain as simple reference implementations but are no longer the active runtime persistence layer.

---

### Milestone C — Checkpointing and True Interrupt-Style HITL

Project 1 now includes checkpointed graph execution and a true interrupt-style HITL graph experiment.

Checkpointing helpers:

```text
build_thread_id(ticket_id)
build_graph_config(thread_id)
create_memory_checkpointer()
```

Checkpointed graph variants:

```text
checkpointed_ticket_graph
checkpointed_approval_resume_graph
```

Checkpointed API endpoints:

```text
POST /tickets/triage/checkpointed
POST /tickets/{ticket_id}/resume/checkpointed
```

True interrupt-style graph experiment:

```text
interruptible_ticket_graph
human_approval_interrupt_node
interrupt(...)
Command(resume={...})
```

This demonstrates graph-level pause/resume behavior with the same `thread_id`.

---

## Project 1 HITL Flow Summary

Stable API-level HITL flow:

```text
POST /tickets/triage
→ high-risk ticket routes to high_risk_review_node
→ preview_high_risk_action generates preview-only action review
→ approval_status = pending
→ no write action executed

POST /tickets/{ticket_id}/approval
→ approval/rejection stored in SQLite

POST /tickets/{ticket_id}/resume
→ approved decision executes simulated write tool once
→ repeated approved resume is idempotency-protected
→ rejected decision blocks safely
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
→ high-risk request reaches human_approval_interrupt_node
→ graph pauses with interrupt(...)

interruptible_ticket_graph.invoke(Command(resume={...}), config=same_config)
→ same graph thread resumes
→ approved path executes simulated write tool
→ rejected path blocks safely
```

---

## Project 1 Tool Layer

```text
billing_node              → lookup_billing_record              → read-only evidence
technical_node            → get_technical_diagnostics          → read-only diagnostic checklist
high_risk_review_node     → preview_high_risk_action           → preview-only action review
execute_approved_action_node → execute_approved_high_risk_action → approved write simulation
```

Tool safety boundary:

```text
Read-only tools may run automatically.
Preview-only tools may run before approval.
Approved write simulations may run only after approval.
Real write tools are intentionally out of scope.
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
OPENAI_API_KEY=dummy-ci-key
```

---

## Planned Project Ladder

This repo is intended to grow into a complete Agentic AI systems portfolio.

Planned projects:

1. **Support Ticket Triage Agent v2** — graph routing, HITL approval, simulated tools, idempotency, SQLite persistence, checkpointed graphs, interrupt-style pause/resume, FastAPI, evals, tracing
2. **Refund Decision Agent** — RAG + policy grounding + billing/refund tools
3. **Human Approval Action Agent** — richer approval policies, durable checkpointing, approval gates, idempotent write tools
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
- read-only vs preview-only vs approved-write tool design
- tool-result state capture
- idempotency for write actions
- SQLite-backed local persistence
- checkpointed graph execution
- interrupt-style HITL pause/resume
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
Status: core engineering milestones complete / final polish in progress
Tests: 70/70 passing
Evals: 5/5 passing
CI: enabled
Next milestone: final polish — demo scripts, architecture docs, Makefile, Dockerfile, and root/project documentation cleanup
```

---

## Author Notes

This lab is being built incrementally to mirror how production AI systems are actually engineered: small safe changes, tests first where possible, explicit state, observable workflows, approval gates, idempotency, persistence, checkpointing, and clear separation between prototype behavior and production-ready behavior.