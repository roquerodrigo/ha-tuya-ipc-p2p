"""Communication error raised by the API client."""

from __future__ import annotations

from .api_client_error import TuyaIpcP2pApiClientError


class TuyaIpcP2pApiClientCommunicationError(
    TuyaIpcP2pApiClientError,
):
    """Exception to indicate a communication error."""
