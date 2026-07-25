import pytest

from mevad.jobs import RetryBackoff, is_retryable_error


def test_retry_classifier_defaults_unknown_errors_to_permanent() -> None:
    assert is_retryable_error("job_execution_failed")
    assert is_retryable_error("job_timed_out")
    assert is_retryable_error("worker_lease_expired")
    assert not is_retryable_error("job_invalid_parameters")
    assert not is_retryable_error("job_resource_limit_exceeded")
    assert not is_retryable_error("unknown_error")
    assert not is_retryable_error(None)


def test_retry_backoff_is_exponential_and_capped() -> None:
    policy = RetryBackoff(base_seconds=5, max_seconds=12)

    assert policy.delay_seconds(attempt_count=1) == 5
    assert policy.delay_seconds(attempt_count=2) == 10
    assert policy.delay_seconds(attempt_count=3) == 12
    assert policy.delay_seconds(attempt_count=10) == 12


def test_retry_backoff_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError):
        RetryBackoff(base_seconds=0)
    with pytest.raises(ValueError):
        RetryBackoff(base_seconds=10, max_seconds=5)
    with pytest.raises(ValueError):
        RetryBackoff().delay_seconds(attempt_count=0)
