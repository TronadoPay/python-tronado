"""Tests for the asynchronous client (mirrors the sync behaviour)."""

from __future__ import annotations

import httpx
import pytest
import respx

from tronado import AsyncTronadoClient
from tronado.exceptions import OrderNotFoundError, TronadoServerError, TronadoTimeoutError
from tronado.models import DollarPrice, OrderTokenData, TronConversion, TronPrice

from .conftest import url

ENVELOPE_OK = {
    "IsSuccessful": True,
    "Code": 200,
    "Message": "",
    "Data": {"Token": "tok", "FullPaymentUrl": "https://t.me/x?start=tok"},
}


@respx.mock
async def test_async_price(async_client: AsyncTronadoClient) -> None:
    respx.post(url("/Tron/GetPriceToToman")).mock(
        return_value=httpx.Response(200, json={"TronPriceToman": 100, "TronPriceDollar": 1})
    )
    result = await async_client.price.tron.get_price_to_toman()
    assert isinstance(result, TronPrice)
    assert result.tron_price_toman == 100


@respx.mock
async def test_async_get_order_token(async_client: AsyncTronadoClient) -> None:
    respx.post(url("/api/v5/GetOrderToken")).mock(
        return_value=httpx.Response(200, json=ENVELOPE_OK)
    )
    token = await async_client.order.get_order_token(
        payment_id="p",
        wallet_address="T",
        tron_amount="1.0",
        callback_url="https://x.com/cb",
    )
    assert isinstance(token, OrderTokenData)
    assert token.token == "tok"


@respx.mock
async def test_async_not_found_raises(async_client: AsyncTronadoClient) -> None:
    respx.post(url("/Order/GetStatus")).mock(
        return_value=httpx.Response(200, json={"Error": "No order found with this txid"})
    )
    with pytest.raises(OrderNotFoundError):
        await async_client.order.get_status(id="x")


@respx.mock
async def test_async_order_token_not_retried(async_client: AsyncTronadoClient) -> None:
    route = respx.post(url("/api/v5/GetOrderToken")).mock(return_value=httpx.Response(500))
    with pytest.raises(TronadoServerError):
        await async_client.order.get_order_token(
            payment_id="p",
            wallet_address="T",
            tron_amount="1.0",
            callback_url="https://x.com/cb",
        )
    assert route.call_count == 1


@respx.mock
async def test_async_idempotent_retries_5xx_then_succeeds(
    async_client: AsyncTronadoClient,
) -> None:
    route = respx.post(url("/Tron/GetPriceToToman")).mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json={"TronPriceToman": 7, "TronPriceDollar": 0.7}),
        ]
    )
    result = await async_client.price.tron.get_price_to_toman()
    assert result.tron_price_toman == 7
    assert route.call_count == 2


@respx.mock
async def test_async_timeout_retried_then_raises(async_client: AsyncTronadoClient) -> None:
    route = respx.post(url("/Tron/GetPriceToToman")).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(TronadoTimeoutError):
        await async_client.price.tron.get_price_to_toman()
    assert route.call_count == 3  # initial + 2 retries


@respx.mock
async def test_async_price_conversions(async_client: AsyncTronadoClient) -> None:
    respx.post(url("/Toman/ConvertToTronWageSubtracted")).mock(
        return_value=httpx.Response(200, json={"TronAmount": 1.5, "TronSunAmount": 1500000})
    )
    conv = await async_client.price.toman.convert_to_tron_wage_subtracted(
        toman=50000, wallet="TXYZ"
    )
    assert isinstance(conv, TronConversion)

    respx.post(url("/Dollar/GetPriceToToman")).mock(
        return_value=httpx.Response(200, json={"DollarPrice": 100783})
    )
    price = await async_client.price.dollar.get_price_to_toman()
    assert isinstance(price, DollarPrice)
    assert price.dollar_price == 100783


async def test_async_context_manager_closes() -> None:
    async with AsyncTronadoClient(api_key="k") as c:
        inner = c._transport._client  # noqa: SLF001 - white-box check
    assert inner.is_closed is True
