"""DataUpdateCoordinator for tuya_ipc_p2p."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER
from .exceptions import (
    TuyaIpcP2pApiClientAuthenticationError,
    TuyaIpcP2pApiClientError,
)

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant

    from .data import TuyaIpcP2pConfigEntry, TuyaIpcP2pPayload

FAILURE_GRACE_PERIOD = timedelta(minutes=5)


class TuyaIpcP2pDataUpdateCoordinator(DataUpdateCoordinator["TuyaIpcP2pPayload"]):
    """
    Polls the account for what the cameras look like from the cloud.

    The video path does not go through here at all: the streams supervise
    themselves and push their frames. This poll only refreshes the name, the
    online flag and the local key of each configured camera — the last of which
    rotates when a device is re-paired, and a rotated key is adopted by the
    running stream on its next session.
    """

    config_entry: TuyaIpcP2pConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        scan_interval: timedelta,
        device_ids: frozenset[str],
        config_entry: TuyaIpcP2pConfigEntry | None = None,
    ) -> None:
        """Bind the coordinator to the cameras the entry configured."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
            always_update=False,
            config_entry=config_entry,
        )
        self._device_ids = device_ids
        self._first_failure_at: datetime | None = None

    async def _async_update_data(self) -> TuyaIpcP2pPayload:
        """Fetch the device list, tolerating outages shorter than the grace period."""
        try:
            data = await self.config_entry.runtime_data.client.async_camera_states(
                self._device_ids
            )
        except TuyaIpcP2pApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except TuyaIpcP2pApiClientError as exception:
            return self._handle_failure(exception)

        self._first_failure_at = None
        self._adopt_rotated_local_keys(data)
        return data

    def _adopt_rotated_local_keys(self, data: TuyaIpcP2pPayload) -> None:
        """
        Hand a rotated local key to the stream that will need it.

        Re-pairing a device changes its local key, which keys the signaling
        payloads and the channel-0 credential. Without this the stream keeps
        offering the old one and the camera stops answering.
        """
        for device_id, stream in self.config_entry.runtime_data.streams.items():
            state = data.get(device_id)
            if state is not None and state["local_key"] != stream.local_key:
                LOGGER.info("Adopting a rotated local key for %s", device_id)
                stream.local_key = state["local_key"]

    def _handle_failure(self, exception: TuyaIpcP2pApiClientError) -> TuyaIpcP2pPayload:
        """
        Serve the last known data while the outage is shorter than the grace period.

        A single failed poll of a cloud API is usually a blip, not an outage,
        yet raising ``UpdateFailed`` immediately marks every entity unavailable
        — which shows up in history, breaks automations that read the state,
        and resolves itself one poll later. Holding the last known values for a
        bounded window trades a little staleness for that stability, and a
        genuine outage still surfaces once the window closes.

        Only failures with data to fall back on are absorbed, and an
        authentication error never reaches here, so re-authentication is still
        prompted at once.
        """
        now = dt_util.utcnow()
        if self._first_failure_at is None:
            self._first_failure_at = now

        last_known_data: TuyaIpcP2pPayload | None = self.data
        if (
            last_known_data is not None
            and now - self._first_failure_at < FAILURE_GRACE_PERIOD
        ):
            LOGGER.warning(
                "Failed to fetch the device list; serving the last known values: %s",
                exception,
            )
            return last_known_data

        raise UpdateFailed(exception) from exception
