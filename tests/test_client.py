"""Tests for client wiring: version registry, env, lifecycle."""

from __future__ import annotations

import httpx
import pytest

from tronado import TronadoClient, available_versions
from tronado.exceptions import TronadoConfigError
from tronado.versions.v5 import V5SyncVersion


def test_available_versions() -> None:
    assert "v5" in available_versions()


def test_version_is_cached(client: TronadoClient) -> None:
    assert client.version() is client.version("v5")
    assert isinstance(client.v5, V5SyncVersion)


def test_unsupported_version_raises(client: TronadoClient) -> None:
    with pytest.raises(TronadoConfigError):
        client.version("v999")


def test_default_version_drives_shortcuts() -> None:
    c = TronadoClient(api_key="k")
    assert c.config.default_version == "v5"
    assert c.order is c.v5.order
    c.close()


def test_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRONADO_API_KEY", "env-key")
    c = TronadoClient()
    assert c.config.api_key == "env-key"
    c.close()


def test_injected_http_client_not_closed_by_client() -> None:
    http_client = httpx.Client()
    c = TronadoClient(api_key="k", http_client=http_client)
    c.close()
    # The caller owns an injected client; close() must not close it.
    assert http_client.is_closed is False
    http_client.close()


def test_context_manager_closes_owned_client() -> None:
    with TronadoClient(api_key="k") as c:
        transport_client = c._transport._client  # noqa: SLF001 - white-box check
    assert transport_client.is_closed is True
