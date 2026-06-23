"""Tests for the price/conversion resources (sync)."""

from __future__ import annotations

from decimal import Decimal

import httpx
import respx

from tronado import TronadoClient
from tronado.models import DollarPrice, PriceWithWage, TronConversion, TronPrice

from .conftest import url


@respx.mock
def test_tron_get_price_to_toman_sends_no_body(client: TronadoClient) -> None:
    route = respx.post(url("/Tron/GetPriceToToman")).mock(
        return_value=httpx.Response(
            200, json={"TronPriceToman": 34374, "TronPriceDollar": 0.3399185}
        )
    )
    result = client.price.tron.get_price_to_toman()
    assert isinstance(result, TronPrice)
    assert result.tron_price_toman == 34374
    assert result.tron_price_dollar == Decimal("0.3399185")

    request = route.calls.last.request
    # No-body endpoints send an empty body, but Content-Type is still set per the docs.
    assert request.content == b""
    assert request.headers["content-type"] == "application/json"
    assert request.headers["x-api-key"] == "test-key"


@respx.mock
def test_tron_get_price_with_wage(client: TronadoClient) -> None:
    route = respx.post(url("/Tron/GetPriceWithWageToToman")).mock(
        return_value=httpx.Response(
            200, json={"ActualAmountToman": 41250, "AmountWithWageToman": 43000}
        )
    )
    result = client.price.tron.get_price_with_wage_to_toman(
        request_code="rc", wallet_address="TXYZ", tron_amount="12.12"
    )
    assert isinstance(result, PriceWithWage)
    assert result.amount_with_wage_toman == 43000
    assert b'"RequestCode":"rc"' in route.calls.last.request.content


@respx.mock
def test_toman_convert_and_dollar_price(client: TronadoClient) -> None:
    respx.post(url("/Toman/ConvertToTronWageSubtracted")).mock(
        return_value=httpx.Response(200, json={"TronAmount": 25.123456, "TronSunAmount": 25123456})
    )
    conv = client.price.toman.convert_to_tron_wage_subtracted(toman=500000, wallet="TXYZ")
    assert isinstance(conv, TronConversion)
    assert conv.tron_amount == Decimal("25.123456")

    respx.post(url("/Toman/GetPriceToToman")).mock(
        return_value=httpx.Response(200, json={"DollarPrice": 100783})
    )
    price = client.price.toman.get_price_to_toman()
    assert isinstance(price, DollarPrice)
    assert price.dollar_price == 100783


@respx.mock
def test_dollar_convert_and_price(client: TronadoClient) -> None:
    respx.post(url("/Dollar/ConvertToTronWageSubtracted")).mock(
        return_value=httpx.Response(200, json={"TronAmount": 25.123456, "TronSunAmount": 25123456})
    )
    conv = client.price.dollar.convert_to_tron_wage_subtracted(dollar="25.5", wallet="TXYZ")
    assert conv.tron_sun_amount == Decimal("25123456")

    respx.post(url("/Dollar/GetPriceToToman")).mock(
        return_value=httpx.Response(200, json={"DollarPrice": 100783})
    )
    assert client.price.dollar.get_price_to_toman().dollar_price == 100783
