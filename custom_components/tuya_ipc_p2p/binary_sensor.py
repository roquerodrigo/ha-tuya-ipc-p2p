"""Binary sensor platform for tuya_ipc_p2p."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .entity import TuyaIpcP2pEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import TuyaIpcP2pCameraConfig, TuyaIpcP2pConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 -- part of the signature Home Assistant calls
    entry: TuyaIpcP2pConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one motion sensor per configured camera."""
    cameras: list[TuyaIpcP2pCameraConfig] = list(entry.data["cameras"])
    async_add_entities(
        TuyaIpcP2pMotionBinarySensor(
            coordinator=entry.runtime_data.coordinator,
            device_id=camera["device_id"],
            fallback_name=camera["name"],
        )
        for camera in cameras
    )


class TuyaIpcP2pMotionBinarySensor(TuyaIpcP2pEntity, BinarySensorEntity):
    """
    Motion derived from the frames the camera already sends.

    These cameras report no motion of their own, so it is read out of how much
    each JPEG differs in size from the one before it — a direct measure of how
    much the scene changed, since a JPEG is only as large as its content is
    complex. It is an indirect signal, and it cannot tell a cat from the lights
    coming on.

    Motion is read from the frames a session delivers, so it only reports while
    the camera is connected. With **Keep connected** off, that is only while
    something is watching.
    """

    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_translation_key = "motion"

    @property
    def unique_id(self) -> str:
        """Return a unique id derived from the Tuya device id."""
        return f"{self._device_id}_motion"

    @property
    def is_on(self) -> bool:
        """Whether the frames currently look like something is moving."""
        return self.camera_stream.motion_detected

    @property
    def available(self) -> bool:
        """
        Whether the motion state means anything right now.

        Nothing can be said about motion while no session is delivering
        frames, so the sensor is unavailable rather than reporting "clear".
        """
        return super().available and self.camera_stream.streaming

    async def async_added_to_hass(self) -> None:
        """Start reporting the stream's motion state."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.camera_stream.add_state_listener(self._on_stream_state)
        )

    def _on_stream_state(self) -> None:
        """Write the new state whenever the stream reports a change."""
        self.async_write_ha_state()
