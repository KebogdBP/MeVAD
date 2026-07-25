"""Bounded retry classification and delay policy."""

from dataclasses import dataclass

TRANSIENT_ERROR_CODES = frozenset(
    {
        "job_execution_failed",
        "job_timed_out",
        "worker_lease_expired",
    }
)


def is_retryable_error(error_code: str | None) -> bool:
    """Return whether a stable worker error is safe to retry."""

    return error_code in TRANSIENT_ERROR_CODES


@dataclass(frozen=True, slots=True)
class RetryBackoff:
    """Deterministic capped exponential retry delay."""

    base_seconds: int = 5
    max_seconds: int = 300

    def __post_init__(self) -> None:
        if not 1 <= self.base_seconds <= 3600:
            raise ValueError("Retry base delay must be between 1 and 3600 seconds.")
        if not self.base_seconds <= self.max_seconds <= 86400:
            raise ValueError("Retry maximum delay must not be shorter than its base.")

    def delay_seconds(self, *, attempt_count: int) -> int:
        if attempt_count < 1:
            raise ValueError("Attempt count must be positive.")
        multiplier: int = 2 ** (attempt_count - 1)
        return min(self.max_seconds, self.base_seconds * multiplier)
