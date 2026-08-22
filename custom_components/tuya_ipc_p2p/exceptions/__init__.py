"""Exception classes for the tuya_ipc_p2p API client."""

from __future__ import annotations

from .api_client_authentication_error import (
    TuyaIpcP2pApiClientAuthenticationError,
)
from .api_client_communication_error import (
    TuyaIpcP2pApiClientCommunicationError,
)
from .api_client_error import TuyaIpcP2pApiClientError

__all__ = [
    "TuyaIpcP2pApiClientAuthenticationError",
    "TuyaIpcP2pApiClientCommunicationError",
    "TuyaIpcP2pApiClientError",
]
