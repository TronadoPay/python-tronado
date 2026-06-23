"""Tests for the Order resource (sync)."""

from __future__ import annotations

import httpx
import pytest
import respx

from tronado import TronadoClient
from tronado.exceptions import OrderNotFoundError
from tronado.models import OrderStatus, OrderTokenData

from .conftest import url

ENVELOPE_OK = {
    "IsSuccessful": True,
    "Code": 200,
    "Message": "",
    "Data": {
        "Token": "1234abcd",
        "FullPaymentUrl": "https://t.me/Tronado_Robot?start=s_1234abcd",
        "ErrorMessage": None,
        "EstimatedTomanAmount": "150000",
        "EstimatedTomanAmountExpireDateUtc": "2025-09-09T12:34:56Z",
    },
}

STATUS_FOUND = {
    "UniqueCode": "UniqueCode",
    "PaymentID": "YourApplicationPaymentID",
    "UserTelegramId": 123456789,
    "Wallet": "TXYZ",
    "Hash": "0xabc",
    "TronAmount": 100.25,
    "ActualTronAmount": 100.00,
    "OrderStatusID": 30,
    "OrderStatusTitle": "PaymentAccepted",
    "IsPaid": True,
    "PaymentDate": "2025-09-09T15:30:00Z",
}


@respx.mock
def test_get_order_token_success(client: TronadoClient) -> None:
    route = respx.post(url("/api/v5/GetOrderToken")).mock(
        return_value=httpx.Response(200, json=ENVELOPE_OK)
    )
    result = client.order.get_order_token(
        payment_id="inv-1",
        wallet_address="TXYZ",
        tron_amount="12.123456",
        callback_url="https://example.com/cb",
        wage_from_business_percentage=0,
    )
    assert isinstance(result, OrderTokenData)
    assert result.token == "1234abcd"
    assert result.estimated_toman_amount == "150000"

    request = route.calls.last.request
    # Auth uses the documented header (not Bearer).
    assert request.headers["x-api-key"] == "test-key"
    assert "authorization" not in request.headers
    # Version is in the path; the wage parameter is in the query string.
    assert request.url.path == "/api/v5/GetOrderToken"
    assert request.url.params["wageFromBusinessPercentage"] == "0"
    # TronAmount is serialized as a JSON number, not a quoted string.
    assert b'"TronAmount":12.123456' in request.content


@pytest.mark.parametrize("wage", [-1, 101, 250])
def test_get_order_token_rejects_out_of_range_wage(client: TronadoClient, wage: int) -> None:
    # Validated locally before any network call is made.
    with pytest.raises(ValueError, match="0 and 100"):
        client.order.get_order_token(
            payment_id="p",
            wallet_address="T",
            tron_amount="1",
            callback_url="https://x.com/cb",
            wage_from_business_percentage=wage,
        )


@respx.mock
def test_get_status_found(client: TronadoClient) -> None:
    respx.post(url("/Order/GetStatus")).mock(return_value=httpx.Response(200, json=STATUS_FOUND))
    status = client.order.get_status(id="TrndOrderID_55")
    assert isinstance(status, OrderStatus)
    assert status.is_payment_accepted is True
    assert status.payment_id == "YourApplicationPaymentID"


@respx.mock
def test_get_status_not_found_raises(client: TronadoClient) -> None:
    respx.post(url("/Order/GetStatus")).mock(
        return_value=httpx.Response(200, json={"Error": "No order found with this txid"})
    )
    try:
        client.order.get_status(id="missing")
    except OrderNotFoundError as exc:
        assert "No order found" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected OrderNotFoundError")


@respx.mock
def test_get_status_by_payment_id_uses_correct_path(client: TronadoClient) -> None:
    route = respx.post(url("/Order/GetStatusByPaymentID")).mock(
        return_value=httpx.Response(200, json=STATUS_FOUND)
    )
    client.order.get_status_by_payment_id(id="inv-1")
    assert route.called
    assert route.calls.last.request.url.path == "/Order/GetStatusByPaymentID"
