"""Version-agnostic building blocks for describing API operations.

An :class:`Operation` is a declarative description of a single endpoint: its HTTP
method, path template, request/response models, and the handful of behavioural flags
the transport needs (enveloped response? not-found sentinel key? safe to retry?).

Resources are thin facades that pick an :class:`Operation`, build the request model and
delegate to the transport. This is what keeps the SDK version-aware: a new API version
is just a new package of ``Operation`` descriptors and resource facades; the transport,
models and error handling are reused unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, Type, TypeVar

from pydantic import BaseModel

#: The response model an operation resolves to. Making :class:`Operation` generic over
#: this lets ``transport.invoke`` return the concrete model type (so resource methods
#: are fully typed without casts).
ResponseT = TypeVar("ResponseT", bound=BaseModel)


@dataclass(frozen=True)
class Operation(Generic[ResponseT]):
    """Declarative description of one API endpoint.

    Attributes:
        name: Stable identifier (used in error messages and logs).
        method: HTTP method (always ``"POST"`` in the current API).
        path_template: URL path with an optional ``{version}`` placeholder, e.g.
            ``"/api/{version}/GetOrderToken"`` or ``"/Order/GetStatus"``.
        request_model: Model type for the JSON body, or ``None`` for no-body endpoints.
        response_model: Model type the (unwrapped) success payload validates into.
        idempotent: Whether the operation is safe to retry. ``GetOrderToken`` is
            ``False`` because it creates a transaction.
        envelope: Whether the response is wrapped in the
            ``{IsSuccessful, Code, Message, Data}`` envelope.
        not_found_key: For flat responses, the JSON key whose presence signals "not
            found" (Tronado returns HTTP 200 with ``{"Error": ...}``).
    """

    name: str
    method: str
    path_template: str
    request_model: Optional[Type[BaseModel]]
    response_model: Type[ResponseT]
    idempotent: bool = True
    envelope: bool = False
    not_found_key: Optional[str] = None


class BaseVersion:
    """Marker base class for a concrete API version binding.

    Concrete versions (e.g. ``V5SyncVersion``) set :attr:`tag` and expose resource
    attributes wired to a transport.
    """

    tag: str = ""


__all__ = ["Operation", "BaseVersion", "ResponseT"]
