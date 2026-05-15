# Final Cleanup Checklist — Support Ticket Triage Agent v2

Use this checklist before marking Project 1 as complete and moving to Project 2.

---

## 1. Local Verification

Run from the project folder:

```zsh
make check
```

Expected:

```text
pytest: 70/70 passed
python -m evals.run_eval: 5/5 passed
```

Also verify individual demos:

```zsh
make demo-interrupt
```

For the API demo, run the API in one terminal:

```zsh
make run-api
```

Then in another terminal:

```zsh
make demo-api
```

Expected demo behavior:

```text
checkpointed triage succeeds
approval is recorded
first resume executes approved write simulation
second resume is skipped by idempotency
```

---

## 2. Docker Verification

Build from the project folder:

```zsh
docker build -t support-ticket-triage-agent-v2 .
```

Run on port `8001` to avoid local `uvicorn` conflicts:

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

Expected:

```json
{
  "status": "ok",
  "classifier_mode": "mock",
  "environment": "docker"
}
```

---

## 3. Git Hygiene

Before committing final changes:

```zsh
git status --short
```

Confirm these are not staged or committed:

```text
.env
.venv/
__pycache__/
.pytest_cache/
*.db
*.sqlite
*.sqlite3
data/support_agent.db
```

The generated SQLite file should stay local:

```text
data/support_agent.db
```

The tracked JSON reference stores should remain empty unless intentionally documenting examples:

```json
{}
```

Files to check:

```text
data/approvals.json
data/action_executions.json
```

---

## 4. Documentation Consistency

Confirm these files agree on current project status:

```text
README.md
../../README.md
docs/hitl_design.md
docs/architecture.md
docs/final_cleanup_checklist.md
```

Current status should say:

```text
pytest: 70/70 passed
evals: 5/5 passed
core engineering milestones complete
final polish in progress / ready for Project 2 after cleanup
```

Docs should mention:

- Milestone A: approved simulated write-tool execution and idempotency
- Milestone B: SQLite-backed approval/action persistence
- Milestone C: checkpointed graphs and interrupt-style HITL pause/resume
- Milestone D: architecture docs, demo scripts, Makefile, Docker support

---

## 5. API Surface Check

Current standard endpoints:

```text
GET  /health
POST /tickets/triage
POST /tickets/{ticket_id}/approval
GET  /tickets/{ticket_id}/approval
POST /tickets/{ticket_id}/resume
```

Current checkpointed endpoints:

```text
POST /tickets/triage/checkpointed
POST /tickets/{ticket_id}/resume/checkpointed
```

Graph-level interrupt experiment:

```text
interruptible_ticket_graph
human_approval_interrupt_node
interrupt(...)
Command(resume={...})
```

The interruptible graph is intentionally tested and demonstrated at graph level, not exposed as a public API endpoint.

---

## 6. Safety Boundary Check

Confirm the project messaging remains accurate:

```text
No real external write action is executed.
Approved write execution is simulated only.
Real billing, CRM, admin, and account tools are intentionally out of scope.
```

Tool safety boundary:

```text
read-only tools may run automatically
preview-only tools may run before approval
approved write simulations may run only after approval
real write tools are intentionally out of scope
```

---

## 7. LangSmith Notes

If adding screenshots or run-inspection notes, capture examples for:

- normal triage run
- high-risk triage run
- checkpointed API run
- approved resume run
- idempotency-skipped second resume run

Useful tags to filter:

```text
support-ticket-triage
api-run
checkpointed-api-run
checkpointed-resume-run
eval-run
classifier:mock
env:local
```

Optional file to add later:

```text
docs/langsmith_run_notes.md
```

---

## 8. CI Check

After each push, verify GitHub Actions:

```text
GitHub → Actions → support-ticket-triage-ci.yml
```

Expected:

```text
pytest passes
python -m evals.run_eval passes
no real OpenAI/LangSmith calls in CI
```

CI should use:

```text
CLASSIFIER_MODE=mock
APP_ENV=ci
LANGSMITH_TRACING=false
OPENAI_API_KEY=dummy-ci-key
```

---

## 9. Final Project 1 Completion Criteria

Project 1 can be considered complete when:

- [x] `make check` passes locally
- [x] `make demo-interrupt` works
- [x] `make demo-api` works with API running
- [x] Docker build succeeds
- [x] Docker `/health` check returns `environment=docker`
- [x] GitHub Actions passes
- [x] no `.env`, `.venv`, cache, or database files are committed
- [x] README, root README, HITL docs, and architecture docs are consistent
- [x] known limitations are clearly documented
- [x] final commit is pushed

---

## 10. Ready for Project 2

Once this checklist is complete, Project 1 can be treated as a portfolio-ready foundation project.

Project 2 can then start cleanly:

```text
Project 2: Refund Decision Agent
Focus: RAG + policy grounding + refund decision workflow + tool safety
```
