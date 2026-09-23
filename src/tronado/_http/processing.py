"""Pure request-preparation and response-processing helpers.

This module holds the request/response *logic* shared by both transports. The
transports themselves only own the imperative I/O loop (and the sync vs. async
``sleep``); everything about *how* to build a request and *how* to interpret a response
lives here, so the two transports cannot drift apart.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from ..config import TronadoConfig
from ..exceptions import (
    OrderNotFoundError,
    TronadoAPIError,
    TronadoAuthenticationError,
    TronadoRateLimitError,
    TronadoServerError,
    TronadoValidationError,
)
from ..models.common import ApiEnvelope

if TYPE_CHECKING:
    from ..versions.base import Operation, ResponseT

#: Local model TypeVar so ``_validate_model`` preserves the concrete model type.
_M = TypeVar("_M", bound=BaseModel)


@dataclass
class PreparedRequest:
    """A fully resolved HTTP request, ready to hand to httpx."""

    method: str
    url: str
    headers: Dict[str, str]
    content: bytes
    params: Optional[Dict[str, Any]]


def _json_default(obj: object) -> object:
    """JSON encoder hook.

    ``Decimal`` is emitted as a JSON *number* (via ``float``) rather than a quoted
    string, matching the documented request bodies. TRON amounts have at most six
    decimal places and modest magnitude, so the float round-trip is exact for our
    domain while keeping ``Decimal`` end-to-end in the public model layer.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def encode_json(payload: Mapping[str, Any]) -> bytes:
    """Serialize a request body to compact UTF-8 JSON bytes."""
    return json.dumps(
        payload, default=_json_default, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def prepare_request(
    config: TronadoConfig,
    operation: Operation[Any],
    request_model: Optional[BaseModel],
    *,
    version: str,
    query: Optional[Mapping[str, Any]] = None,
) -> PreparedRequest:
    """Build a :class:`PreparedRequest` for ``operation``.

    Args:
        config: Active client configuration.
        operation: The operation descriptor (path template, models, …).
        request_model: A validated request model instance, or ``None`` for operations
            without input.
        version: API version tag substituted into the path template (e.g. ``"v5"``).
        query: Optional query-string parameters.

    Raises:
        TronadoAPIError: If the operation requires a body but none was supplied.
        TronadoConfigError: If the operation requires the API key and none is configured.
    """
    path = operation.path_template.format(version=version)
    url = f"{config.base_url}{path}"

    if operation.request_model is None:
        # Operations without input still send ``{}``: the docs warn that IIS rejects a
        # POST without a body (no Content-Length) with 411 Length Required.
        content = encode_json({})
    else:
        if request_model is None:
            raise TronadoAPIError(
                f"Operation {operation.name!r} requires a request body but none was given."
            )
        body = request_model.model_dump(by_alias=True, exclude_none=False)
        content = encode_json(body)

    headers = config.build_headers(authenticated=operation.requires_auth)

    params: Optional[Dict[str, Any]] = None
    if query:
        params = {k: v for k, v in query.items() if v is not None}
        params = params or None

    return PreparedRequest(
        method=operation.method,
        url=url,
        headers=headers,
        content=content,
        params=params,
    )


def _safe_json(text: str) -> Any:
    try:
        return json.loads(text) if text else None
    except (ValueError, TypeError):
        return None


def _extract_message(data: Any, default: str) -> str:
    if isinstance(data, dict):
        for key in ("Message", "message", "Error", "error", "ErrorMessage"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
    return default


def _validate_model(model_cls: Type[_M], data: Any, status_code: int) -> _M:
    """Validate ``data`` into ``model_cls``, wrapping schema errors as API errors."""
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        raise TronadoAPIError(
            f"Could not parse Tronado response into {model_cls.__name__}.",
            status_code=status_code,
            response=data,
        ) from exc


def process_response(
    operation: Operation[ResponseT],
    status_code: int,
    text: str,
) -> ResponseT:
    """Turn a raw HTTP response into a typed model or raise a mapped exception.

    Note:
        Retryable statuses (429/5xx) reach this function only once the retry budget is
        exhausted; at that point they become terminal exceptions.
    """
    data = _safe_json(text)

    # --- transport/auth-level statuses take precedence -------------------------------
    if status_code == 401:
        raise TronadoAuthenticationError(
            _extract_message(data, "API key is wrong or not specified."),
            status_code=status_code,
            code=data.get("Code") if isinstance(data, dict) else None,
            response=data,
        )
    if status_code == 429:
        raise TronadoRateLimitError(
            _extract_message(data, "Rate limit exceeded."),
            status_code=status_code,
            response=data,
        )
    if status_code >= 500:
        raise TronadoServerError(
            _extract_message(data, "Tronado server error."),
            status_code=status_code,
            response=data,
        )

    # --- enveloped operations (GetOrderToken) ----------------------------------------
    if operation.envelope:
        envelope = _validate_model(ApiEnvelope, data, status_code)
        if not envelope.is_successful:
            message = envelope.message or "Tronado request was not successful."
            if envelope.code == -1:
                raise TronadoAuthenticationError(
                    message, status_code=status_code, code=envelope.code, response=data
                )
            raise TronadoValidationError(
                message, status_code=status_code, code=envelope.code, response=data
            )
        return _validate_model(operation.response_model, envelope.data, status_code)

    # --- flat operations -------------------------------------------------------------
    if (
        operation.not_found_key
        and isinstance(data, dict)
        and operation.not_found_key in data
    ):
        raise OrderNotFoundError(
            str(data[operation.not_found_key]),
            status_code=status_code,
            response=data,
        )

    if status_code >= 400:
        raise TronadoValidationError(
            _extract_message(data, f"Request failed with status {status_code}."),
            status_code=status_code,
            response=data,
        )

    return _validate_model(operation.response_model, data, status_code)


__all__ = [
    "PreparedRequest",
    "encode_json",
    "prepare_request",
    "process_response",
]
