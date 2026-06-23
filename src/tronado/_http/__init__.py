"""Internal HTTP transport layer.

Public code should not depend on these classes directly; they are an implementation
detail of the high-level clients. Re-exported here for internal convenience and tests.
"""

from __future__ import annotations

from .async_transport import AsyncTransport
from .base import BaseTransport
from .processing import PreparedRequest, prepare_request, process_response
from .sync_transport import SyncTransport

__all__ = [
    "BaseTransport",
    "SyncTransport",
    "AsyncTransport",
    "PreparedRequest",
    "prepare_request",
    "process_response",
]
