"""Shared Pydantic base model and reusable field types.

The Tronado API uses PascalCase JSON keys (``PaymentID``, ``TronAmount``, …). We expose
idiomatic ``snake_case`` Python attributes and map them with field aliases, so models
both *parse* PascalCase responses and *serialize* PascalCase requests.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Union

from pydantic import BaseModel, BeforeValidator, ConfigDict

# Matches an ISO-8601 timestamp whose fractional-seconds component has more than the
# six digits Python's datetime supports (Tronado emits 7-digit ".1830000" fractions).
_OVERLONG_FRACTION = re.compile(r"^(.*\.\d{6})\d+(.*)$")


def _normalize_datetime(value: object) -> object:
    """Truncate over-precise fractional seconds so ``datetime`` parsing succeeds.

    ``2026-06-20T15:27:00.1830000`` -> ``2026-06-20T15:27:00.183000``. Non-string and
    well-formed values pass through untouched.
    """
    if isinstance(value, str):
        match = _OVERLONG_FRACTION.match(value)
        if match:
            return match.group(1) + match.group(2)
    return value


def _to_decimal(value: object) -> object:
    """Coerce ``int``/``float`` to ``Decimal`` via ``str`` to avoid binary float error.

    ``Decimal(0.1)`` is noisy; ``Decimal("0.1")`` is exact. Strings and existing
    ``Decimal`` values pass through.
    """
    if isinstance(value, float):
        return Decimal(str(value))
    return value


#: ``datetime`` field that tolerates Tronado's 7-digit fractional seconds and the
#: ``Z`` suffix used elsewhere in the API.
FlexibleDateTime = Annotated[datetime, BeforeValidator(_normalize_datetime)]

#: ``Decimal`` field that accepts ``int``/``float``/``str`` without float rounding error.
TronDecimal = Annotated[Decimal, BeforeValidator(_to_decimal)]

#: Convenience alias for amount inputs accepted at the public API boundary.
AmountInput = Union[Decimal, int, float, str]


class TronadoModel(BaseModel):
    """Base model for all SDK request/response types.

    Configuration:
        * ``populate_by_name`` — construct models with Python field names *or* aliases.
        * ``extra="ignore"`` — forward-compatible: unknown API fields are dropped rather
          than raising, so a future API revision won't break deserialization.
        * ``str_strip_whitespace`` — trim incidental whitespace from string inputs.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
        ser_json_inf_nan="constants",
    )


__all__ = [
    "TronadoModel",
    "FlexibleDateTime",
    "TronDecimal",
    "AmountInput",
]
