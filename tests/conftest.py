"""Shared pytest fixtures and helpers for the Tronado SDK test-suite."""

from __future__ import annotations

from typing import Iterator

import pytest

from tronado import AsyncTronadoClient, TronadoClient
from tronado.constants import DEFAULT_BASE_URL

BASE_URL = DEFAULT_BASE_URL


def url(path: str) -> str:
    """Build an absolute URL against the default base URL."""
    return f"{BASE_URL}{path}"


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure environment variables never leak into tests."""
    monkeypatch.delenv("TRONADO_API_KEY", raising=False)
    monkeypatch.delenv("TRONADO_BASE_URL", raising=False)


@pytest.fixture
def client() -> Iterator[TronadoClient]:
    """A sync client with retries fast (zero backoff) for deterministic tests."""
    c = TronadoClient(api_key="test-key", max_retries=2, backoff_factor=0.0)
    yield c
    c.close()


@pytest.fixture
async def async_client() -> Iterator[AsyncTronadoClient]:
    """An async client with zero backoff."""
    c = AsyncTronadoClient(api_key="test-key", max_retries=2, backoff_factor=0.0)
    yield c
    await c.aclose()
