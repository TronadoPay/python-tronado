"""Tests for error mapping, retries, and idempotency."""

from __future__ import annotations

import httpx
import pytest
import respx

from tronado import TronadoClient
from tronado.exceptions import (
    TronadoAuthenticationError,
    TronadoConnectionError,
    TronadoRateLimitError,
    TronadoServerError,
    TronadoTimeoutError,
    TronadoValidationError,
)

from .conftest import url

UNAUTHORIZED = {
    "IsSuccessful": False,
    "Code": -1,
    "Message": "Api key is wrong or not specified.",
    "Data": None,
}


def _order_token(client: TronadoClient):
    return client.order.get_order_token(
        payment_id="p",
        wallet_address="T",
        tron_amount="1",
        callback_url="https://x.com/cb",
    )


@respx.mock
def test_401_maps_to_authentication_error(client: TronadoClient) -> None:
    respx.post(url("/api/v5/GetOrderToken")).mock(
        return_value=httpx.Response(401, json=UNAUTHORIZED)
    )
    with pytest.raises(TronadoAuthenticationError) as exc:
        _order_token(client)
    assert exc.value.status_code == 401


@respx.mock
def test_envelope_unsuccessful_maps_to_validation_error(client: TronadoClient) -> None:
    respx.post(url("/api/v5/GetOrderToken")).mock(
        return_value=httpx.Response(
            200,
            json={"IsSuccessful": False, "Code": 422, "Message": "Bad wallet", "Data": None},
        )
    )
    with pytest.raises(TronadoValidationError) as exc:
        _order_token(client)
    assert "Bad wallet" in str(exc.value)
    assert exc.value.code == 422


@respx.mock
def test_rate_limit_maps_to_rate_limit_error(client: TronadoClient) -> None:
    # 429 is retryable; exhaust retries then surface the error.
    respx.post(url("/Tron/GetPriceToToman")).mock(return_value=httpx.Response(429, json={}))
    with pytest.raises(TronadoRateLimitError):
        client.price.tron.get_price_to_toman()


@respx.mock
def test_idempotent_op_retries_5xx_then_succeeds(client: TronadoClient) -> None:
    route = respx.post(url("/Tron/GetPriceToToman")).mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(200, json={"TronPriceToman": 1, "TronPriceDollar": 0.1}),
        ]
    )
    result = client.price.tron.get_price_to_toman()
    assert result.tron_price_toman == 1
    assert route.call_count == 2  # one retry


@respx.mock
def test_idempotent_op_exhausts_retries_and_raises_server_error(client: TronadoClient) -> None:
    route = respx.post(url("/Tron/GetPriceToToman")).mock(return_value=httpx.Response(503))
    with pytest.raises(TronadoServerError):
        client.price.tron.get_price_to_toman()
    # client fixture uses max_retries=2 -> 3 total attempts.
    assert route.call_count == 3


@respx.mock
def test_get_order_token_is_not_retried_on_5xx(client: TronadoClient) -> None:
    route = respx.post(url("/api/v5/GetOrderToken")).mock(return_value=httpx.Response(500))
    with pytest.raises(TronadoServerError):
        _order_token(client)
    # Non-idempotent: exactly one attempt, no retries (avoids duplicate orders).
    assert route.call_count == 1


@respx.mock
def test_timeout_retried_then_raises(client: TronadoClient) -> None:
    route = respx.post(url("/Tron/GetPriceToToman")).mock(
        side_effect=httpx.ReadTimeout("slow")
    )
    with pytest.raises(TronadoTimeoutError):
        client.price.tron.get_price_to_toman()
    assert route.call_count == 3  # initial + 2 retries


@respx.mock
def test_connection_error_retried_then_succeeds(client: TronadoClient) -> None:
    route = respx.post(url("/Tron/GetPriceToToman")).mock(
        side_effect=[
            httpx.ConnectError("down"),
            httpx.Response(200, json={"TronPriceToman": 5, "TronPriceDollar": 0.5}),
        ]
    )
    result = client.price.tron.get_price_to_toman()
    assert result.tron_price_toman == 5
    assert route.call_count == 2


@respx.mock
def test_get_order_token_not_retried_on_connection_error(client: TronadoClient) -> None:
    route = respx.post(url("/api/v5/GetOrderToken")).mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(TronadoConnectionError):
        _order_token(client)
    assert route.call_count == 1
