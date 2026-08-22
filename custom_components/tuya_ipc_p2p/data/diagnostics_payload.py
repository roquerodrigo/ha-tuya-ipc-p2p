"""Typed top-level shape returned by async_get_config_entry_diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from .camera_state import TuyaIpcP2pCameraState
    from .diagnostics_entry import TuyaIpcP2pDiagnosticsEntry
    from .stream_diagnostics import TuyaIpcP2pStreamDiagnostics


class TuyaIpcP2pDiagnosticsPayload(TypedDict):
    """Top-level shape returned by async_get_config_entry_diagnostics."""

    entry: TuyaIpcP2pDiagnosticsEntry
    coordinator_data: dict[str, TuyaIpcP2pCameraState] | None
    streams: dict[str, TuyaIpcP2pStreamDiagnostics]
