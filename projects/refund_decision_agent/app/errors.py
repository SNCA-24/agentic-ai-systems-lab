class RefundDecisionError(Exception):
    """Base error for refund decision workflow failures."""


class RefundDecisionValidationError(RefundDecisionError):
    """Raised when request or schema validation fails."""


class RefundDecisionWorkflowError(RefundDecisionError):
    """Raised when workflow execution cannot complete safely."""
