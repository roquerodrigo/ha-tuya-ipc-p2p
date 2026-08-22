"""TuyaIpcP2pEntity base class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER, MODEL
from .coordinator import TuyaIpcP2pDataUpdateCoordinator

if TYPE_CHECKING:
    from tuya_ipc_p2p_sdk import CameraStream

    from .data import TuyaIpcP2pCameraState, TuyaIpcP2pPayload


class TuyaIpcP2pEntity(CoordinatorEntity[TuyaIpcP2pDataUpdateCoordinator]):
    """Base entity for one Tuya IPC camera."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TuyaIpcP2pDataUpdateCoordinator,
        device_id: str,
        fallback_name: str,
    ) -> None:
        """Bind the entity to one camera of the account."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._fallback_name = fallback_name

    @property
    def device_id(self) -> str:
        """The Tuya device id this entity belongs to."""
        return self._device_id

    @property
    def camera_state(self) -> TuyaIpcP2pCameraState | None:
        """
        What the last poll knew about this camera, if anything.

        ``coordinator.data`` is typed as the payload because that is the
        coordinator's binding, but at runtime it is None until the first
        successful refresh.
        """
        data: TuyaIpcP2pPayload | None = self.coordinator.data
        if data is None:
            return None
        return data.get(self._device_id)

    @property
    def camera_stream(self) -> CameraStream:
        """
        The supervised stream of this camera.

        Not named ``stream``: Home Assistant's ``Camera`` writes an attribute
        of that name for its own stream worker, and a read-only property would
        shadow it.
        """
        return self.coordinator.config_entry.runtime_data.streams[self._device_id]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this camera."""
        state = self.camera_state
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=state["name"] if state else self._fallback_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            serial_number=self._device_id,
        )

    @property
    def available(self) -> bool:
        """
        Whether the camera is reachable.

        A camera the account reports as offline stays unavailable even while
        the coordinator itself is healthy: nothing this integration does can
        bring a session up against hardware that is not on the network.
        """
        state = self.camera_state
        return super().available and state is not None and state["online"]
