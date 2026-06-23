"""Unit tests for the pure retry-decision helpers."""

from __future__ import annotations

import pytest

from tronado._http.retry import (
    compute_backoff,
    is_retryable_status,
    retry_after_seconds,
    should_retry,
)


@pytest.mark.parametrize(
    "code,expected",
    [(200, False), (404, False), (429, True), (500, True), (503, True)],
)
def test_is_retryable_status(code: int, expected: bool) -> None:
    assert is_retryable_status(code) is expected


def test_should_retry_respects_idempotency() -> None:
    # Non-idempotent operations are never retried, even with budget left.
    assert should_retry(attempt=0, max_retries=3, idempotent=False) is False
    # Idempotent operations retry until the budget is exhausted.
    assert should_retry(attempt=0, max_retries=3, idempotent=True) is True
    assert should_retry(attempt=2, max_retries=3, idempotent=True) is True
    assert should_retry(attempt=3, max_retries=3, idempotent=True) is False


def test_compute_backoff_is_bounded_and_grows() -> None:
    # Zero factor -> zero delay (used by the test-suite for instant retries).
    assert compute_backoff(attempt=5, backoff_factor=0.0, max_backoff=30, jitter=1.0) == 0.0
    # Grows with attempt and stays within [0, max_backoff].
    low = compute_backoff(attempt=0, backoff_factor=1.0, max_backoff=30, jitter=0.0)
    high = compute_backoff(attempt=3, backoff_factor=1.0, max_backoff=30, jitter=1.0)
    assert 0.0 <= low <= high <= 30.0
    # max_backoff caps the result.
    assert compute_backoff(attempt=20, backoff_factor=1.0, max_backoff=5, jitter=1.0) <= 5.0


def test_retry_after_seconds() -> None:
    assert retry_after_seconds({"Retry-After": "12"}) == 12.0
    assert retry_after_seconds({"retry-after": "0"}) == 0.0
    assert retry_after_seconds({}) is None
    assert retry_after_seconds({"Retry-After": "Wed, 21 Oct 2099 07:28:00 GMT"}) is None
