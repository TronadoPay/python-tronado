"""Cross-cutting response wrappers."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import TronadoModel


class ApiEnvelope(TronadoModel):
    """The ``{IsSuccessful, Code, Message, Data}`` wrapper used by ``GetOrderToken``.

    Only the versioned ``GetOrderToken`` endpoint wraps its payload this way. The SDK
    parses the envelope generically, checks :attr:`is_successful`, and then validates
    :attr:`data` into the concrete response model for the operation.
    """

    is_successful: bool = Field(alias="IsSuccessful")
    code: int = Field(default=0, alias="Code")
    message: str = Field(default="", alias="Message")
    data: Any = Field(default=None, alias="Data")


__all__ = ["ApiEnvelope"]
