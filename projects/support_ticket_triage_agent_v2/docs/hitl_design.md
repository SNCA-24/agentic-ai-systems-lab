# Human-in-the-Loop Approval Design

This document explains the human-in-the-loop approval design for `support_ticket_triage_agent_v2`.

The project started as a safe API-level approval simulation and has now evolved into a production-style HITL learning system with:

- risk-aware graph routing
- approval-state tracking
- simulated read-only and preview-only tools
- approved simulated write-tool execution
- idempotency protection
- SQLite-backed persistence
- checkpointed graph variants
- true LangGraph `interrupt()` / `Command(resume=...)` pause/resume experiment

The implementation remains intentionally conservative: no real external write action is executed.

---

## Current Purpose

The project handles high-risk support tickets safely by separating these concerns:

```text
classification
→ risk-aware routing
→ preview-only action review
→ human approval
→ approved simulated write-tool execution
→ idempotency-protected action record
→ audit-friendly response
```

Core safety rule:

```text
No high-risk write action can run unless approval is explicit.
```

Examples of high-risk tickets:

- restore deleted users
- grant admin access
- delete accounts
- large refund requests
- security incidents
- data loss
- irreversible actions

---

## Milestone Summary

### Milestone A — Approved Simulated Write-Tool Execution

Milestone A added the approved action execution path.

Before Milestone A:

```text
approval recorded
→ resume safely
→ no action execution
```

After Milestone A:

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
- `data/action_executions.json` as the original local JSON action-execution record store
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

The approved write tool is still simulated. It records:

```json
{
  "tool_name": "execute_approved_high_risk_action",
  "tool_type": "approved_write_simulation",
  "write_action_executed": true,
  "side_effect": "simulated_only",
  "duplicate_prevented": false
}
```

Repeated resume calls with the same idempotency key return:

```json
{
  "status": "skipped",
  "duplicate_prevented": true,
  "skip_reason": "idempotency_key_already_executed"
}
```

---

### Milestone B — SQLite-Backed Persistence

Milestone B replaced the active runtime persistence layer with SQLite.

Current active runtime store:

```text
data/support_agent.db
```

The generated SQLite database is ignored by Git and created automatically by `app/db.py`.

Current tables:

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

Current runtime behavior:

```text
approval decisions       → stored in SQLite approval_records
action execution records → stored in SQLite action_execution_records
```

The earlier JSON-backed stores remain as reference/local-simple implementations:

```text
app/approval_store.py
app/action_store.py
data/approvals.json
data/action_executions.json
```

They are no longer the active runtime persistence layer.

---

### Milestone C — Checkpointing and True Interrupt-Style HITL

Milestone C completed the transition from simple API-level resume simulation toward real graph-orchestration HITL patterns.

Milestone C was completed in three stages.

#### C.1 — Checkpointing Helpers

Added:

- `app/checkpointing.py`
- `create_memory_checkpointer()`
- `build_thread_id(ticket_id)`
- `build_graph_config(thread_id)`

Thread IDs follow this format:

```text
support-ticket:<ticket_id>
```

Example:

```text
support-ticket:HITL-001
```

#### C.2 — Checkpointed Graph Variants and API Endpoints

Added checkpoint-enabled graph variants:

```text
checkpointed_ticket_graph
checkpointed_approval_resume_graph
```

Added checkpointed API endpoints:

```text
POST /tickets/triage/checkpointed
POST /tickets/{ticket_id}/resume/checkpointed
```

These expose `thread_id` in the API response and run through checkpoint-enabled graph variants.

This step proved that graph runs can be associated with stable `thread_id` values.

#### C.3 — True Interrupt-Style HITL Experiment

Added the actual interrupt-style graph experiment:

```text
interruptible_ticket_graph
human_approval_interrupt_node
```

The interrupt node uses:

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

The graph pauses and returns an approval request payload.

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

This is the strongest HITL pattern in the project because the same graph thread pauses and later resumes using `Command(resume=...)`.

---

## Current Implemented HITL Flows

The project now supports three HITL-related execution styles.

### 1. Stable API-Level Resume Flow

This is the original production-safe API path.

```text
POST /tickets/triage
→ high-risk ticket routes to high_risk_review_node
→ preview_high_risk_action generates preview-only action review
→ approval_status = pending
→ no write action executed

POST /tickets/{ticket_id}/approval
→ approval/rejection stored in SQLite

POST /tickets/{ticket_id}/resume
→ approval decision loaded from SQLite
→ approved decision executes simulated write tool once
→ repeated resume is idempotency-protected
→ rejected decision blocks safely
```

### 2. Checkpointed API Flow

This is a checkpoint-enabled API path that exposes `thread_id`.

```text
POST /tickets/triage/checkpointed
→ runs checkpointed_ticket_graph
→ returns thread_id

POST /tickets/{ticket_id}/resume/checkpointed
→ runs checkpointed_approval_resume_graph
→ returns thread_id
```

This path is useful for showing how LangGraph checkpointer configuration and thread IDs work.

### 3. Interruptible Graph Experiment

This is the true pause/resume experiment.

```text
interruptible_ticket_graph.invoke(initial_state, config={"configurable": {"thread_id": ...}})
→ high-risk request reaches human_approval_interrupt_node
→ graph pauses with interrupt(...)

interruptible_ticket_graph.invoke(Command(resume={...}), config=same_config)
→ same graph thread resumes
→ approved path executes simulated write tool
→ rejected path blocks safely
```

This is currently tested at the graph level, not exposed as a public API endpoint.

---

## Current Persistence Design

Active runtime persistence is SQLite-backed.

```text
data/support_agent.db
```

Tables:

| Table | Purpose |
|---|---|
| `approval_records` | Stores latest approval/rejection decision per ticket |
| `action_execution_records` | Stores idempotency-protected approved action execution records |

SQLite store modules:

```text
app/sqlite_approval_store.py
app/sqlite_action_store.py
```

Reference JSON store modules:

```text
app/approval_store.py
app/action_store.py
```

The JSON implementations are kept as simple reference versions but are not active runtime stores.

---

## Approval State Fields

The graph state includes approval-related fields:

```python
approval_status: ApprovalStatus
approval_id: Optional[str]
approval_notes: Optional[str]
approved_by: Optional[str]
```

Supported approval statuses:

```text
not_required
pending
approved
rejected
expired
```

Meaning:

| Status | Meaning |
|---|---|
| `not_required` | Normal request; no human approval needed |
| `pending` | High-risk request waiting for human decision |
| `approved` | Human approved the request |
| `rejected` | Human rejected the request |
| `expired` | Approval window expired or decision is no longer valid |

---

## Tool Layer

The project includes a simulated tool layer for safe enterprise-style tool design.

Current pre-approval tools:

| Tool | Type | Used By | Purpose |
|---|---|---|---|
| `lookup_billing_record` | read-only | `billing_node` | Returns mock billing evidence for billing/duplicate-charge tickets |
| `get_technical_diagnostics` | read-only | `technical_node` | Returns mock diagnostics checklist for technical tickets |
| `preview_high_risk_action` | preview-only | `high_risk_review_node` | Generates high-risk action preview without executing any write action |

Current approved-action tool:

| Tool | Type | Used By | Purpose |
|---|---|---|---|
| `execute_approved_high_risk_action` | approved write simulation | `execute_approved_action_node` | Simulates approved high-risk action execution with idempotency protection |

Tool safety boundary:

```text
read-only tools may run automatically
preview-only tools may run before approval
approved write simulations may run only after approval
real write tools are intentionally out of scope
```

Tool outputs are stored in graph state as:

```text
tool_results
```

---

## Idempotency Design

Idempotency prevents repeated resume calls from duplicating approved write actions.

Idempotency key format:

```text
<ticket_id>:<approval_id>:<action_type>
```

Example:

```text
HITL-001:approval_123:simulated_high_risk_action
```

Execution behavior:

```text
first approved resume
→ idempotency key not found
→ simulated write action executes
→ execution record stored

second approved resume with same approval/action
→ idempotency key already exists
→ execution is skipped
→ previous execution result is returned
```

This demonstrates the production pattern used to prevent duplicate refunds, duplicate account restores, repeated permission grants, or other repeated side effects.

---

## Current API Endpoints

### Standard triage

```text
POST /tickets/triage
```

Classifies and routes a ticket through the stable non-checkpointed triage graph.

---

### Checkpointed triage

```text
POST /tickets/triage/checkpointed
```

Runs the checkpoint-enabled triage graph and returns a `thread_id`.

---

### Record approval

```text
POST /tickets/{ticket_id}/approval
```

Records an approval or rejection in SQLite.

Example request:

```json
{
  "approved": true,
  "approval_id": "approval_123",
  "approved_by": "manager_001",
  "approval_notes": "Requester verified and action approved."
}
```

---

### Get approval

```text
GET /tickets/{ticket_id}/approval
```

Returns the latest approval decision for the ticket from SQLite.

---

### Standard resume

```text
POST /tickets/{ticket_id}/resume
```

Loads approval from SQLite and runs the stable approval resume graph.

Approved response includes:

```text
workflow_path:
approval_resume_entry_node
→ approval_approved_node
→ execute_approved_action_node
```

---

### Checkpointed resume

```text
POST /tickets/{ticket_id}/resume/checkpointed
```

Loads approval from SQLite and runs the checkpoint-enabled approval resume graph.

Returns:

```text
thread_id
workflow_path
last_tool_result
tool_results_count
trace_events_count
```

---

## Current Implementation Files

```text
app/api.py                    → FastAPI endpoints for triage, approval, resume, checkpointed flows
app/db.py                     → SQLite database initialization
app/sqlite_approval_store.py  → active SQLite-backed approval persistence
app/sqlite_action_store.py    → active SQLite-backed action execution persistence
app/approval_store.py         → legacy/reference JSON-backed approval store
app/action_store.py           → legacy/reference JSON-backed action execution store
app/graph.py                  → normal, checkpointed, and interruptible graph definitions
app/nodes.py                  → routing, approval, interrupt, and execution nodes
app/tools.py                  → simulated read-only and preview-only tools
app/write_tools.py            → approved simulated write tool with idempotency
app/checkpointing.py          → checkpointer, thread_id, graph config helpers
app/state.py                  → graph state fields
app/schemas.py                → request/response schemas
```

Relevant tests:

```text
tests/test_api.py                    → API-level triage, approval, resume, checkpointed endpoint tests
tests/test_routing.py                → graph routing and approval resume tests
tests/test_trace_events.py           → trace event tests
tests/test_tools.py                  → read-only and preview-only tool tests
tests/test_write_tools.py            → approved write-tool and idempotency tests
tests/test_sqlite_approval_store.py  → SQLite approval persistence tests
tests/test_sqlite_action_store.py    → SQLite action persistence tests
tests/test_checkpointing.py          → checkpoint helper and checkpointed graph tests
tests/test_interruptible_graph.py    → true interrupt()/Command(resume=...) tests
```

---

## Current Test Coverage

The current test suite covers:

- mock classifier behavior
- deterministic routing behavior
- high-risk routing
- trace events
- read-only tools
- preview-only high-risk action tool
- approved simulated write tool
- idempotency behavior
- SQLite approval persistence
- SQLite action execution persistence
- standard approval API flow
- checkpointed API flow
- checkpointing helper utilities
- checkpointed graph variants
- true interrupt-style HITL graph pause/resume
- rejected approval blocking behavior

Current expected local verification:

```text
pytest: 70/70 passed
python -m evals.run_eval: 5/5 passed
```

---

## Why This Design Is Useful

This design demonstrates several production agent principles:

```text
LLM classifies.
Code routes.
High-risk actions are isolated.
Tool outputs are captured as structured evidence.
Read-only and preview-only tools are separated from write tools.
Approval changes authorization state.
Approved action execution is idempotency-protected.
SQLite persists approvals and action execution records.
Checkpointed graphs use thread_id-based configuration.
LangGraph interrupt() can pause for human approval.
Command(resume=...) can resume the same graph thread.
Rejected approvals block safely.
```

---

## Current Boundaries and Limitations

The project is production-style, but still intentionally local and simulated.

Current boundaries:

- write execution is simulated, not connected to a real CRM/billing/admin system
- SQLite is local, not a production Postgres/MySQL deployment
- `MemorySaver` checkpointing is local/in-memory, not durable across process restarts
- interruptible graph is tested at graph level, not exposed as a public API endpoint
- no real identity verification for approvers yet
- no role-based authorization for approval decisions yet
- no expiration policy for approval windows yet
- no distributed locking or concurrent worker coordination yet

---

## Future Production Target Design

A production-grade version would evolve toward:

```text
high-risk graph node
→ preview-only action tool
→ LangGraph interrupt/checkpoint
→ approval captured from authorized reviewer
→ approval identity and permission verified
→ graph resumes using durable thread_id
→ approved write tool executes with idempotency key
→ execution result stored in durable database
→ audit trail persists approval + execution record
→ monitoring/evaluation tracks regressions
```

Additional future production requirements:

- durable checkpoint store beyond `MemorySaver`
- database migrations
- Postgres-backed persistence
- approver identity verification
- approval expiration timestamps
- role-based permission checks
- audit log tables
- idempotency-key uniqueness guarantees at database level
- status reconciliation after write-tool timeout
- LangSmith dataset-based evaluation for HITL paths
- deployment configuration and API auth

---

## Design Rule

The most important rule for this project is:

```text
Approval changes authorization state.
Approval does not automatically mean unsafe execution.
Execution still goes through typed tools, idempotency, persistence, and traceability.
```

A safe production flow is:

```text
classify
→ route
→ preview
→ interrupt / approve
→ verify approval
→ execute with idempotency
→ persist result
→ audit
```

The current project implements this pattern with simulated tools, SQLite persistence, checkpointed graphs, and a true interrupt-style graph experiment.