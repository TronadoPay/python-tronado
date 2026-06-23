"""Synchronous HTTP transport built on :class:`httpx.Client`."""

from __future__ import annotations

import time
from typing import Any, Mapping, Optional

import httpx
from pydantic import BaseModel

from ..config import TronadoConfig
from ..exceptions import TronadoConnectionError, TronadoTimeoutError
from ..versions.base import Operation, ResponseT
from .base import BaseTransport
from .processing import prepare_request, process_response
from .retry import retry_after_seconds


class SyncTransport(BaseTransport):
    """Executes operations synchronously, applying retries and error mapping.

    Args:
        config: Active client configuration.
        http_client: Optional pre-built :class:`httpx.Client`. When supplied, the caller
            owns its lifecycle; otherwise the transport creates and closes its own.
    """

    def __init__(
        self, config: TronadoConfig, *, http_client: Optional[httpx.Client] = None
    ) -> None:
        super().__init__(config)
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=httpx.Timeout(config.timeout))

    def invoke(
        self,
        operation: Operation[ResponseT],
        request_model: Optional[BaseModel] = None,
        *,
        version: str,
        query: Optional[Mapping[str, Any]] = None,
    ) -> ResponseT:
        """Send ``operation`` and return its typed response model.

        Retries are applied to idempotent operations on timeouts, connection errors and
        retryable HTTP statuses (429/5xx). Non-idempotent operations (order creation)
        are never retried.
        """
        prepared = prepare_request(
            self._config, operation, request_model, version=version, query=query
        )
        attempt = 0
        while True:
            try:
                response = self._client.request(
                    prepared.method,
                    prepared.url,
                    headers=prepared.headers,
                    content=prepared.content,
                    params=prepared.params,
                )
            except httpx.TimeoutException as exc:
                if self._retry_allowed(attempt, idempotent=operation.idempotent):
                    time.sleep(self._backoff(attempt))
                    attempt += 1
                    continue
                raise TronadoTimeoutError(
                    f"Request to {prepared.url} timed out after {self._config.timeout}s.",
                    cause=exc,
                ) from exc
            except httpx.RequestError as exc:
                if self._retry_allowed(attempt, idempotent=operation.idempotent):
                    time.sleep(self._backoff(attempt))
                    attempt += 1
                    continue
                raise TronadoConnectionError(
                    f"Failed to reach {prepared.url}: {exc}", cause=exc
                ) from exc

            if self._status_is_retryable(
                response.status_code, attempt, idempotent=operation.idempotent
            ):
                delay = retry_after_seconds(response.headers) or self._backoff(attempt)
                time.sleep(delay)
                attempt += 1
                continue

            return process_response(operation, response.status_code, response.text)

    def close(self) -> None:
        """Close the underlying HTTP client (only if this transport created it)."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> SyncTransport:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


__all__ = ["SyncTransport"]
