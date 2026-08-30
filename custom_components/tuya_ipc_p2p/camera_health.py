"""Watches one stream for the camera having stopped answering offers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .issues import async_review_camera_power_state

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from tuya_ipc_p2p_sdk import CameraStream

    from .data import TuyaIpcP2pConfigEntry


class TuyaIpcP2pCameraHealth:
    """
    Turns a camera that has stopped answering into a repair issue.

    The stream reports every state change it makes — a frame arriving, motion
    starting — so the reporting is edge-triggered: an issue is only touched
    when the answer actually changes.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: TuyaIpcP2pConfigEntry,
        stream: CameraStream,
        camera_name: str,
    ) -> None:
        """Watch one camera of one entry."""
        self._hass = hass
        self._entry = entry
        self._stream = stream
        self._camera_name = camera_name
        self._reported = False

    def async_watch(self) -> Callable[[], None]:
        """Start following the stream, and return the callback that stops it."""
        return self._stream.add_state_listener(self._handle_state_change)

    def _handle_state_change(self) -> None:
        """Raise or withdraw the issue when, and only when, the answer changes."""
        needs_power_cycle = self._stream.needs_power_cycle
        if needs_power_cycle == self._reported:
            return
        self._reported = needs_power_cycle
        async_review_camera_power_state(
            self._hass,
            self._entry,
            self._stream.device_id,
            self._camera_name,
            needs_power_cycle=needs_power_cycle,
        )
