"""Diagnostics support for tuya_ipc_p2p."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from homeassistant.components.diagnostics import async_redact_data

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.core import HomeAssistant

    from .data import (
        TuyaIpcP2pCameraState,
        TuyaIpcP2pConfigEntry,
        TuyaIpcP2pDiagnosticsEntry,
        TuyaIpcP2pDiagnosticsPayload,
        TuyaIpcP2pStreamDiagnostics,
    )

# The local key is what encrypts the signaling and derives the channel-0
# credential, so it belongs in a dump no more than the password does.
TO_REDACT: frozenset[str] = frozenset(
    {"email", "password", "country_code", "local_key"}
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001 -- part of the signature Home Assistant calls
    entry: TuyaIpcP2pConfigEntry,
) -> TuyaIpcP2pDiagnosticsPayload:
    """Return diagnostics for a config entry."""
    redacted_data = cast(
        "Mapping[str, str]",
        async_redact_data(dict(entry.data), set(TO_REDACT)),
    )
    redacted_options = cast(
        "Mapping[str, str | int]",
        async_redact_data(dict(entry.options), set(TO_REDACT)),
    )
    diag_entry: TuyaIpcP2pDiagnosticsEntry = {
        "title": entry.title,
        "version": entry.version,
        "domain": entry.domain,
        "data": redacted_data,
        "options": redacted_options,
    }
    streams: dict[str, TuyaIpcP2pStreamDiagnostics] = {
        device_id: {
            "running": stream.running,
            "streaming": stream.streaming,
            "motion_detected": stream.motion_detected,
            "viewer_count": stream.viewer_count,
            "last_frame_bytes": (
                len(stream.last_frame) if stream.last_frame is not None else None
            ),
        }
        for device_id, stream in entry.runtime_data.streams.items()
    }
    coordinator_data: dict[str, TuyaIpcP2pCameraState] | None = (
        entry.runtime_data.coordinator.data
    )
    return {
        "entry": diag_entry,
        "coordinator_data": (
            cast(
                "dict[str, TuyaIpcP2pCameraState]",
                async_redact_data(coordinator_data, set(TO_REDACT)),
            )
            if coordinator_data is not None
            else None
        ),
        "streams": streams,
    }
