# Cancellation Policy

## Cancellation Timestamp Handling

- The cancellation timestamp is the source of truth for determining whether a later charge happened after cancellation.
- A charge after cancellation is reviewed against the recorded cancellation timestamp and the charge finalization timestamp.

## Post-Cancellation Charges

- A finalized charge posted after a confirmed cancellation is generally refundable when the service period should have ended before billing.
- A pending authorization created near the cancellation event is not automatically refundable until it becomes a finalized charge.

## Evidence Quality

- If the cancellation timestamp is missing, duplicated, or inconsistent with billing events, the case should not be auto-decided.
- Conflicting evidence or unclear evidence about cancellation timing must escalate to manual review.
