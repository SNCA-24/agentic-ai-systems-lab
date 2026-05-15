

# Human-in-the-Loop Approval Design

This document explains the current human-in-the-loop approval design for `support_ticket_triage_agent_v2` and how it should evolve toward a production-grade durable approval workflow.

---

## Current Purpose

The project handles high-risk support tickets safely by separating three concerns:

```text
classification
→ risk-aware routing
→ human approval simulation
→ safe resume response
```

The current implementation is intentionally conservative:

```text
No high-risk write action is executed automatically.
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

## Current Implemented HITL Flow

The current flow is API-level and simulation-based.

```text
1. POST /tickets/triage
   → ticket is classified
   → high-risk request routes to high_risk_review_node
   → approval_status = pending
   → no write action is executed

2. POST /tickets/{ticket_id}/approval
   → human approval/rejection is recorded
   → approval is stored in an in-memory approval store

3. GET /tickets/{ticket_id}/approval
   → latest approval decision is returned

4. POST /tickets/{ticket_id}/resume
   → approval decision is loaded
   → approved decision routes to approval_approved_node
   → rejected decision routes to approval_rejected_node
   → missing/pending/expired decision is safely blocked
```

---

## Current Boundary

The current implementation is **not durable checkpointing yet**.

It is best described as:

```text
API-level HITL simulation with safe approval resume behavior.
```

Current limitations:

- approval store is in-memory
- approval decisions are lost when API process restarts
- no persistent LangGraph checkpoint resume yet
- no real write tool execution yet
- no approval expiration enforcement beyond state/status handling
- no identity/authorization verification for approvers yet

This is acceptable for the current learning milestone because the system demonstrates the safety pattern without performing real side effects.

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

## Current Safety Rule

High-risk requests must not execute write actions directly.

Current high-risk behavior:

```text
high-risk ticket
→ high_risk_review_node
→ approval_status = pending
→ final response explains that human approval is required
→ no write action is executed
```

This prevents unsafe behavior like:

```text
User: Restore 80 deleted users.
Agent: Done.
```

Correct behavior:

```text
User: Restore 80 deleted users.
Agent: This is high-risk and requires human approval. No write action has been executed.
```

---

## Resume Behavior

The resume endpoint currently converts stored approval decisions into a safe response path.

Approved decision:

```text
POST /tickets/{ticket_id}/resume
→ approval_resume_entry_node
→ approval_approved_node
→ safe response saying approval was recorded
→ no write action executed
```

Rejected decision:

```text
POST /tickets/{ticket_id}/resume
→ approval_resume_entry_node
→ approval_rejected_node
→ safe blocked response
```

Missing/pending/expired decision:

```text
POST /tickets/{ticket_id}/resume
→ safe blocked response
```

---

## Current API Endpoints

### Triage ticket

```text
POST /tickets/triage
```

Classifies the ticket and routes it through the graph.

High-risk result should include:

```json
{
  "risk_level": "high",
  "needs_human_review": true,
  "approval_status": "pending",
  "workflow_path": ["validate_input", "classify_ticket", "high_risk_review_node"]
}
```

---

### Record approval

```text
POST /tickets/{ticket_id}/approval
```

Records approval/rejection in the in-memory approval store.

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

Returns the latest approval decision for the ticket.

---

### Resume workflow

```text
POST /tickets/{ticket_id}/resume
```

Uses the latest approval decision to route into a safe resume graph.

---

## Why This Design Is Useful

This design demonstrates several production agent principles:

```text
LLM classifies.
Code routes.
High-risk actions are isolated.
Human approval is represented explicitly in state.
Approval decisions are auditable.
Resume behavior is safe by default.
No write action executes without approval.
```

---

## Production Target Design

The future production-grade version should use durable graph checkpointing.

Target flow:

```text
high-risk graph node
→ LangGraph interrupt/checkpoint
→ user or manager approval captured externally
→ graph resumes using thread_id
→ approval_id is verified
→ action preview is generated
→ write tool executes only if approved
→ idempotency key prevents duplicate execution
→ audit log persists the decision trail
```

---

## Production Requirements Still Needed

Before real write tools are introduced, the system should add:

- durable checkpointing
- persistent approval store
- approval expiration timestamps
- approval identity verification
- permission checks for approvers
- idempotency keys for write tools
- action preview step before execution
- durable audit logs
- status reconciliation after write-tool timeout
- LangSmith dataset-based evaluation for approval paths

---

## Design Rule

The most important rule for this project is:

```text
Approval changes authorization state.
Approval does not automatically mean immediate execution.
```

A safe production flow is:

```text
classify
→ verify
→ preview
→ approve
→ execute with idempotency
→ audit
```

The current project has implemented the early approval simulation stage and safe resume behavior. Real tool execution remains intentionally out of scope for now.