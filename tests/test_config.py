"""Tests for TronadoConfig."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from tronado import TronadoConfig
from tronado.constants import API_KEY_HEADER, DEFAULT_BASE_URL
from tronado.exceptions import TronadoConfigError


def test_defaults() -> None:
    cfg = TronadoConfig(api_key="k")
    assert cfg.base_url == DEFAULT_BASE_URL
    assert cfg.default_version == "v5"
    assert cfg.max_retries >= 0
    assert cfg.timeout > 0


def test_missing_api_key_only_fails_for_authenticated_headers() -> None:
    # The price endpoints are public, so a config without a key is valid...
    cfg = TronadoConfig()
    assert cfg.api_key is None
    assert API_KEY_HEADER not in cfg.build_headers(authenticated=False)
    # ...but an endpoint that needs the key cannot be called without one.
    with pytest.raises(TronadoConfigError, match="API key"):
        cfg.build_headers()


def test_blank_api_key_is_treated_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRONADO_API_KEY", "")
    assert TronadoConfig().api_key is None


def test_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRONADO_API_KEY", "from-env")
    cfg = TronadoConfig()
    assert cfg.api_key == "from-env"


def test_base_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRONADO_BASE_URL", "https://staging.example.com/")
    cfg = TronadoConfig(api_key="k")
    assert cfg.base_url == "https://staging.example.com"  # trailing slash stripped


def test_trailing_slash_stripped() -> None:
    cfg = TronadoConfig(api_key="k", base_url="https://example.com/")
    assert cfg.base_url == "https://example.com"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"api_key": "k", "base_url": "ftp://nope"},
        {"api_key": "k", "timeout": 0},
        {"api_key": "k", "max_retries": -1},
        {"api_key": "k", "backoff_factor": -0.5},
    ],
)
def test_invalid_settings_raise(kwargs: dict) -> None:
    with pytest.raises(TronadoConfigError):
        TronadoConfig(**kwargs)


def test_build_headers_includes_api_key_and_content_type() -> None:
    cfg = TronadoConfig(api_key="secret", default_headers={"X-Trace": "abc"})
    headers = cfg.build_headers()
    assert headers[API_KEY_HEADER] == "secret"
    assert headers["X-Trace"] == "abc"
    # Content-Type is always sent, matching the documented contract for every endpoint.
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"


def test_build_headers_omits_api_key_for_public_endpoints() -> None:
    headers = TronadoConfig(api_key="secret").build_headers(authenticated=False)
    assert API_KEY_HEADER not in headers
    assert headers["Content-Type"] == "application/json"


def test_default_headers_cannot_override_api_key() -> None:
    cfg = TronadoConfig(api_key="real", default_headers={API_KEY_HEADER: "fake"})
    assert cfg.build_headers()[API_KEY_HEADER] == "real"


def test_config_is_frozen() -> None:
    cfg = TronadoConfig(api_key="secret")
    with pytest.raises(FrozenInstanceError):
        cfg.timeout = 5  # type: ignore[misc]


def test_default_headers_are_read_only() -> None:
    cfg = TronadoConfig(api_key="k", default_headers={"X-A": "1"})
    with pytest.raises(TypeError):
        cfg.default_headers["X-B"] = "2"  # type: ignore[index]


def test_default_headers_snapshot_isolated_from_caller() -> None:
    source = {"X-A": "1"}
    cfg = TronadoConfig(api_key="k", default_headers=source)
    source["X-B"] = "2"  # mutating the original must not affect the config
    assert "X-B" not in cfg.default_headers


def test_repr_redacts_api_key() -> None:
    assert "secret" not in repr(TronadoConfig(api_key="secret"))
