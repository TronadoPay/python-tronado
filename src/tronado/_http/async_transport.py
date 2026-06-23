"""Asynchronous HTTP transport built on :class:`httpx.AsyncClient`.

This mirrors :class:`tronado._http.sync_transport.SyncTransport` exactly; the only
differences are ``await`` on the network call and ``asyncio.sleep`` for backoff. All
request-building, retry-decision and response-mapping *logic* is the shared, pure code
in :mod:`tronado._http.processing` and :mod:`tronado._http.retry`.
"""

from __future__ import annotations

import asyncio
from typing import Any, Mapping, Optional

import httpx
from pydantic import BaseModel

from ..config import TronadoConfig
from ..exceptions import TronadoConnectionError, TronadoTimeoutError
from ..versions.base import Operation, ResponseT
from .base import BaseTransport
from .processing import prepare_request, process_response
from .retry import retry_after_seconds


class AsyncTransport(BaseTransport):
    """Executes operations asynchronously, applying retries and error mapping.

    Args:
        config: Active client configuration.
        http_client: Optional pre-built :class:`httpx.AsyncClient`. When supplied, the
            caller owns its lifecycle.
    """

    def __init__(
        self, config: TronadoConfig, *, http_client: Optional[httpx.AsyncClient] = None
    ) -> None:
        super().__init__(config)
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=httpx.Timeout(config.timeout))

    async def invoke(
        self,
        operation: Operation[ResponseT],
        request_model: Optional[BaseModel] = None,
        *,
        version: str,
        query: Optional[Mapping[str, Any]] = None,
    ) -> ResponseT:
        """Send ``operation`` and return its typed response model (awaitable)."""
        prepared = prepare_request(
            self._config, operation, request_model, version=version, query=query
        )
        attempt = 0
        while True:
            try:
                response = await self._client.request(
                    prepared.method,
                    prepared.url,
                    headers=prepared.headers,
                    content=prepared.content,
                    params=prepared.params,
                )
            except httpx.TimeoutException as exc:
                if self._retry_allowed(attempt, idempotent=operation.idempotent):
                    await asyncio.sleep(self._backoff(attempt))
                    attempt += 1
                    continue
                raise TronadoTimeoutError(
                    f"Request to {prepared.url} timed out after {self._config.timeout}s.",
                    cause=exc,
                ) from exc
            except httpx.RequestError as exc:
                if self._retry_allowed(attempt, idempotent=operation.idempotent):
                    await asyncio.sleep(self._backoff(attempt))
                    attempt += 1
                    continue
                raise TronadoConnectionError(
                    f"Failed to reach {prepared.url}: {exc}", cause=exc
                ) from exc

            if self._status_is_retryable(
                response.status_code, attempt, idempotent=operation.idempotent
            ):
                delay = retry_after_seconds(response.headers) or self._backoff(attempt)
                await asyncio.sleep(delay)
                attempt += 1
                continue

            return process_response(operation, response.status_code, response.text)

    async def aclose(self) -> None:
        """Close the underlying async HTTP client (only if this transport created it)."""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncTransport:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()


__all__ = ["AsyncTransport"]
