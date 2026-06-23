"""Pure, side-effect-free retry-decision helpers.

These functions contain *all* of the retry policy logic and are shared verbatim by the
synchronous and asynchronous transports. Keeping them pure makes the policy trivially
unit-testable and guarantees both transports behave identically.
"""

from __future__ import annotations

from typing import Mapping, Optional

#: HTTP status codes that are safe to retry for idempotent operations.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def is_retryable_status(status_code: int) -> bool:
    """Return whether ``status_code`` warrants a retry (for idempotent operations)."""
    return status_code in RETRYABLE_STATUS_CODES


def should_retry(*, attempt: int, max_retries: int, idempotent: bool) -> bool:
    """Decide whether another attempt is allowed.

    Args:
        attempt: Zero-based index of the attempt that just failed.
        max_retries: Configured maximum number of retries.
        idempotent: Whether the operation is safe to repeat. Non-idempotent operations
            (e.g. order creation) are never retried.

    Returns:
        ``True`` if a further attempt should be made.
    """
    if not idempotent:
        return False
    return attempt < max_retries


def compute_backoff(
    *,
    attempt: int,
    backoff_factor: float,
    max_backoff: float,
    jitter: float,
) -> float:
    """Compute the sleep (seconds) before the next retry using exponential backoff.

    Args:
        attempt: Zero-based index of the attempt that just failed.
        backoff_factor: Base multiplier.
        max_backoff: Hard ceiling for the returned delay.
        jitter: A value in ``[0, 1)`` (supplied by the caller, typically
            ``random.random()``) used to spread retries and avoid thundering herds.

    Returns:
        Number of seconds to sleep, in ``[0, max_backoff]``.
    """
    base = backoff_factor * (2.0 ** attempt)
    base = min(base, max_backoff)
    # Full jitter, scaled to [0.5, 1.0) of base so we never sleep for ~0s on a hit.
    delay = base * (0.5 + 0.5 * jitter)
    return max(0.0, min(delay, max_backoff))


def retry_after_seconds(headers: Mapping[str, str]) -> Optional[float]:
    """Parse a ``Retry-After`` header expressed as an integer number of seconds.

    Only the numeric (delta-seconds) form is honoured; HTTP-date forms are ignored and
    normal backoff applies instead.
    """
    raw = headers.get("Retry-After") or headers.get("retry-after")
    if not raw:
        return None
    try:
        value = float(raw.strip())
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


__all__ = [
    "RETRYABLE_STATUS_CODES",
    "is_retryable_status",
    "should_retry",
    "compute_backoff",
    "retry_after_seconds",
]
