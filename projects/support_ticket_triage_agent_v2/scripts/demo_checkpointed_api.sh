

#!/bin/zsh

# Demo: checkpointed FastAPI endpoints and idempotent approved resume.
#
# Run from the project folder after starting the API in another terminal:
#
#   uvicorn app.api:app --reload
#
# Then run:
#
#   zsh scripts/demo_checkpointed_api.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
TICKET_ID="DEMO-CKPT-001"
APPROVAL_ID="approval_demo_ckpt_001"

print_section() {
  echo "\n============================================================"
  echo "$1"
  echo "============================================================"
}

print_section "1. Health check"
curl -s "${BASE_URL}/health" | python -m json.tool

print_section "2. Checkpointed high-risk triage"
curl -s -X POST "${BASE_URL}/tickets/triage/checkpointed" \
  -H "Content-Type: application/json" \
  -d "{\"ticket_id\":\"${TICKET_ID}\",\"user_message\":\"Our admin deleted 80 users. Can you restore them immediately?\"}" \
  | python -m json.tool

print_section "3. Record human approval"
curl -s -X POST "${BASE_URL}/tickets/${TICKET_ID}/approval" \
  -H "Content-Type: application/json" \
  -d "{\"approved\":true,\"approval_id\":\"${APPROVAL_ID}\",\"approved_by\":\"demo_manager\",\"approval_notes\":\"Demo approval for checkpointed API flow.\"}" \
  | python -m json.tool

print_section "4. First checkpointed resume: approved write simulation should execute"
curl -s -X POST "${BASE_URL}/tickets/${TICKET_ID}/resume/checkpointed" \
  | python -m json.tool

print_section "5. Second checkpointed resume: duplicate execution should be skipped by idempotency"
curl -s -X POST "${BASE_URL}/tickets/${TICKET_ID}/resume/checkpointed" \
  | python -m json.tool

print_section "Demo complete"
echo "Expected behavior: first resume has last_tool_result.status=success; second resume has status=skipped and duplicate_prevented=true."