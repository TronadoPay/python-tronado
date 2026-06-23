"""Shared transport behaviour (retry math, jitter source)."""

from __future__ import annotations

import random

from ..config import TronadoConfig
from .retry import compute_backoff, is_retryable_status, should_retry


class BaseTransport:
    """Common, transport-agnostic helpers for the sync and async transports.

    Subclasses implement the actual (a)synchronous request loop; everything decision-
    related is delegated to the pure helpers in :mod:`tronado._http.retry` from here so
    both transports share one policy.
    """

    def __init__(self, config: TronadoConfig) -> None:
        self._config = config

    @property
    def config(self) -> TronadoConfig:
        return self._config

    def _retry_allowed(self, attempt: int, *, idempotent: bool) -> bool:
        return should_retry(
            attempt=attempt,
            max_retries=self._config.max_retries,
            idempotent=idempotent,
        )

    def _status_is_retryable(self, status_code: int, attempt: int, *, idempotent: bool) -> bool:
        return is_retryable_status(status_code) and self._retry_allowed(
            attempt, idempotent=idempotent
        )

    def _backoff(self, attempt: int) -> float:
        # random.random() is the jitter source; the math itself is pure & tested.
        return compute_backoff(
            attempt=attempt,
            backoff_factor=self._config.backoff_factor,
            max_backoff=self._config.max_backoff,
            jitter=random.random(),
        )


__all__ = ["BaseTransport"]
