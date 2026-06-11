# Refund Decision Agent v1 Design

## Summary

Project 2 implements a policy-grounded refund decision workflow inside `projects/refund_decision_agent/`. The v1 system is deterministic by default, uses local synthetic Markdown policies plus mock JSON fixtures, persists decision records to `data/decision_records.json`, and does not execute real refunds or require live LLM access for tests, evals, demos, or local runs.

## Goals

- Build a LangGraph-based refund decision workflow with deterministic routing.
- Retrieve local policy snippets from synthetic Markdown policy files.
- Load customer and billing evidence from read-only JSON fixtures.
- Produce structured refund eligibility decisions using typed state and Pydantic schemas.
- Flag high-value, enterprise, ambiguous, conflicting, or missing-data cases for review or escalation.
- Expose the workflow through a thin FastAPI endpoint.
- Provide traceability through `workflow_path` and `trace_events`.
- Keep the project reproducible in mock mode with no API keys required.

## Non-Goals

- Real refund execution.
- Real payment processor integrations.
- Real customer or billing data.
- Production-grade persistence.
- Vector database retrieval.
- LLM-dependent execution paths for core tests or demos.

## Architecture

The workflow is linear until the decision step:

```text
validate input
-> classify intent
-> retrieve policy snippets
-> load mock customer and billing evidence
-> run deterministic eligibility logic
-> route deterministically to a response node
-> persist one structured JSON decision record
```

`app/graph.py` owns orchestration and deterministic routing. `app/nodes.py` owns node behavior and state mutation. `app/policy_store.py` loads and retrieves policy sections from local Markdown files. `app/tools.py` exposes read-only fixture access. `app/decision_engine.py` owns refund logic and review thresholds. `app/tracing.py` owns path and trace helpers. `app/api.py` stays a thin request/response wrapper over graph invocation.

## State And Schemas

The graph state should be explicit and audit-friendly. It must include request identifiers, customer input, classification fields, retrieved policy docs, billing evidence, customer context, refund decision fields, policy basis, evidence summary, workflow tracking, trace events, errors, final response, and final status.

Pydantic schemas should define the external request/response contract and the internal structured artifacts used across nodes. The response schema should omit internal traces by default and expose them only when debug output is explicitly requested.

## Policy Retrieval

Policy retrieval is deterministic and local. The policy store should:

- load Markdown policy files from `data/policies/`
- split them into sections by headings
- score sections by keyword overlap against the request text and detected intent
- return the top relevant snippets with source metadata

This v1 retrieval path should be simple enough to inspect in code review and easy to replace later with embeddings or a vector store without changing graph behavior.

## Mock Evidence Tools

Mock tools should read only from local JSON fixtures and never mutate external state. They should support:

- customer profile lookup
- subscription status lookup
- recent charge lookup
- cancellation timestamp lookup
- refund history lookup

Missing records must return safe structured defaults rather than crashing the workflow.

## Decision Logic

The decision engine should be deterministic and policy-aligned. It must explicitly handle:

- duplicate charge eligibility
- post-cancellation charge eligibility
- outside-window ineligibility
- high-value review threshold
- enterprise review requirement
- conflicting evidence escalation
- missing customer or billing evidence escalation

`HIGH_VALUE_REFUND_THRESHOLD = 100.0` should be the default review threshold. The engine returns a structured decision object, and graph routing must use only deterministic Python logic derived from that object and the error state.

## Routing And Responses

The graph should route from `decide_refund_eligibility_node` to exactly one terminal response node:

- `eligible_response_node`
- `ineligible_response_node`
- `human_review_required_node`
- `escalation_response_node`

Terminal nodes should produce customer-safe language. No final response may claim that a refund was issued or executed. The response may say the customer appears eligible, is not eligible, requires manual review, or needs follow-up because the available evidence is incomplete or conflicting.

## Persistence

Decision persistence should use append-only JSON at `data/decision_records.json`. Each persisted record should include:

- `request_id`
- `customer_id`
- `refund_eligible`
- `refund_amount`
- `risk_level`
- `needs_human_review`
- `final_node`
- `status`
- `decision_reason`
- `policy_basis`
- `evidence_summary`
- `timestamp`

Persistence failures must be captured in state errors and trace events without crashing the graph or hiding the user-facing decision.

## Configuration

`CLASSIFIER_MODE=mock` is the default and must support all local tests, evals, demos, and API runs without API keys. Optional live mode can be isolated behind config and a small classifier interface, but v1 behavior must remain centered on deterministic mock classification.

LangSmith settings should remain optional and disabled by default. The configuration layer must not force users to configure OpenAI credentials for local verification.

## Testing And Evaluation

The test suite should cover:

- policy section loading and retrieval relevance
- mock tool behavior and missing-customer safety
- deterministic decision rules
- graph routing by scenario
- safety constraints such as no refund execution and no “refund issued” wording
- API request/response behavior

The eval runner should load JSON scenarios, run the graph, and assert eligibility, risk level, review flag, terminal node, and safe language constraints.

## Documentation Scope

`projects/refund_decision_agent/README.md` and the PRD should describe JSON decision records as the v1 persistence path. SQLite may be mentioned only as a future improvement, not as an implemented default.

## Known v1 Limits

- Retrieval is keyword-scored rather than semantic.
- Decision persistence is JSON-based and not concurrency-robust.
- The workflow is designed for local demoability rather than production operations.
- Optional live LLM support, if present, is a non-default extension point rather than a core dependency.
