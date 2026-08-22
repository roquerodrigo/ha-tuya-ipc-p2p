"""Custom types for tuya_ipc_p2p."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from .camera_config import TuyaIpcP2pCameraConfig
from .camera_state import TuyaIpcP2pCameraState
from .config_data import TuyaIpcP2pConfigData
from .credentials import TuyaIpcP2pCredentials
from .diagnostics_entry import TuyaIpcP2pDiagnosticsEntry
from .diagnostics_payload import TuyaIpcP2pDiagnosticsPayload
from .options_data import TuyaIpcP2pOptionsData
from .runtime import TuyaIpcP2pData
from .stream_diagnostics import TuyaIpcP2pStreamDiagnostics

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | Mapping[str, JsonValue]
type JsonObject = Mapping[str, JsonValue]

type TuyaIpcP2pPayload = dict[str, TuyaIpcP2pCameraState]

type TuyaIpcP2pConfigEntry = ConfigEntry[TuyaIpcP2pData]

__all__ = [
    "JsonObject",
    "JsonPrimitive",
    "JsonValue",
    "TuyaIpcP2pCameraConfig",
    "TuyaIpcP2pCameraState",
    "TuyaIpcP2pConfigData",
    "TuyaIpcP2pConfigEntry",
    "TuyaIpcP2pCredentials",
    "TuyaIpcP2pData",
    "TuyaIpcP2pDiagnosticsEntry",
    "TuyaIpcP2pDiagnosticsPayload",
    "TuyaIpcP2pOptionsData",
    "TuyaIpcP2pPayload",
    "TuyaIpcP2pStreamDiagnostics",
]
