"""Tests for the price/conversion resources (sync)."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
import respx

from tronado import TronadoClient
from tronado.models import DollarPrice, PriceWithWage, TronConversion, TronPrice

from .conftest import url


@respx.mock
def test_tron_get_price_to_toman_sends_empty_json_body(client: TronadoClient) -> None:
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
    # Endpoints without input still send `{}`: IIS answers a bodiless POST with 411.
    assert request.content == b"{}"
    assert request.headers["content-type"] == "application/json"
    # The price endpoints are public, so the API key is not sent to them.
    assert "x-api-key" not in request.headers


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
    # Authenticated by RequestCode in the body, not by the API key header.
    assert b'"RequestCode":"rc"' in route.calls.last.request.content
    assert "x-api-key" not in route.calls.last.request.headers


@respx.mock
def test_toman_convert_and_dollar_price(client: TronadoClient) -> None:
    respx.post(url("/Toman/ConvertToTronWageSubtracted")).mock(
        return_value=httpx.Response(200, json={"TronAmount": 25.123456, "TronSunAmount": 25123456})
    )
    conv = client.price.toman.convert_to_tron_wage_subtracted(toman=500000, wallet="TXYZ")
    assert isinstance(conv, TronConversion)
    assert conv.tron_amount == Decimal("25.123456")


@respx.mock
def test_toman_get_price_to_toman_is_deprecated(client: TronadoClient) -> None:
    # /Toman/GetPriceToToman is no longer documented; it still works but warns.
    respx.post(url("/Toman/GetPriceToToman")).mock(
        return_value=httpx.Response(200, json={"DollarPrice": 100783})
    )
    with pytest.warns(DeprecationWarning, match="price.dollar.get_price_to_toman"):
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


@respx.mock
def test_price_endpoints_work_without_an_api_key() -> None:
    # The docs make every price endpoint public, so no key is needed to call them.
    routes = {
        "/Tron/GetPriceToToman": {"TronPriceToman": 1, "TronPriceDollar": 1},
        "/Tron/GetPriceWithWageToToman": {"ActualAmountToman": 1, "AmountWithWageToman": 1},
        "/Toman/ConvertToTronWageSubtracted": {"TronAmount": 1, "TronSunAmount": 1},
        "/Dollar/ConvertToTronWageSubtracted": {"TronAmount": 1, "TronSunAmount": 1},
        "/Dollar/GetPriceToToman": {"DollarPrice": 1},
    }
    mocked = [
        respx.post(url(path)).mock(return_value=httpx.Response(200, json=body))
        for path, body in routes.items()
    ]
    with TronadoClient() as keyless:
        assert keyless.config.api_key is None
        keyless.price.tron.get_price_to_toman()
        keyless.price.tron.get_price_with_wage_to_toman(
            request_code="rc", wallet_address="T", tron_amount=1
        )
        keyless.price.toman.convert_to_tron_wage_subtracted(toman=1, wallet="T")
        keyless.price.dollar.convert_to_tron_wage_subtracted(dollar=1, wallet="T")
        keyless.price.dollar.get_price_to_toman()
    for route in mocked:
        assert route.call_count == 1
        assert "x-api-key" not in route.calls.last.request.headers
