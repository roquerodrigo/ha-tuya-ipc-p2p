"""Camera platform for tuya_ipc_p2p."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from aiohttp import web
from homeassistant.components.camera import Camera
from homeassistant.helpers.event import async_call_later

from .const import (
    CONF_KEEP_CONNECTED,
    DEFAULT_KEEP_CONNECTED,
    IDLE_SHUTDOWN_SECONDS,
    LOGGER,
    MJPEG_BOUNDARY,
    SNAPSHOT_WARMUP_SECONDS,
)
from .entity import TuyaIpcP2pEntity

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import TuyaIpcP2pDataUpdateCoordinator
    from .data import TuyaIpcP2pCameraConfig, TuyaIpcP2pConfigEntry

_PART_HEADER = (
    f"--{MJPEG_BOUNDARY}\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n"
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 -- part of the signature Home Assistant calls
    entry: TuyaIpcP2pConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one camera entity per configured camera."""
    cameras: list[TuyaIpcP2pCameraConfig] = list(entry.data["cameras"])
    async_add_entities(
        TuyaIpcP2pCamera(
            coordinator=entry.runtime_data.coordinator,
            device_id=camera["device_id"],
            fallback_name=camera["name"],
        )
        for camera in cameras
    )


class TuyaIpcP2pCamera(TuyaIpcP2pEntity, Camera):
    """
    One Tuya IPC camera, served as MJPEG and JPEG snapshots.

    The camera speaks MJPEG and nothing else, so no stream source is offered:
    Home Assistant renders the MJPEG endpoint this entity serves directly,
    which avoids the stream analysis an RTSP source of a couple of frames a
    second never finishes.
    """

    _attr_name = None

    def __init__(
        self,
        coordinator: TuyaIpcP2pDataUpdateCoordinator,
        device_id: str,
        fallback_name: str,
    ) -> None:
        """Bind the entity to one camera and arm its on-demand bookkeeping."""
        TuyaIpcP2pEntity.__init__(self, coordinator, device_id, fallback_name)
        Camera.__init__(self)
        self._cancel_idle_shutdown: Callable[[], None] | None = None

    @property
    def unique_id(self) -> str:
        """Return a unique id derived from the Tuya device id."""
        return f"{self._device_id}_camera"

    @property
    def keep_connected(self) -> bool:
        """
        Whether the session is held open rather than brought up on demand.

        These cameras serve one client at a time, so holding the session means
        the vendor app cannot connect while Home Assistant is set up.
        """
        options = self.coordinator.config_entry.options
        value = options.get(CONF_KEEP_CONNECTED, DEFAULT_KEEP_CONNECTED)
        return bool(value)

    @property
    def is_streaming(self) -> bool:
        """Whether frames are currently arriving from this camera."""
        return self.camera_stream.streaming

    @property
    def is_on(self) -> bool:
        """Whether the camera is enabled; it has no power control of its own."""
        return True

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """
        Return the most recent JPEG the camera produced.

        Bringing a cold session up takes several seconds — login, signaling,
        relay, the channel-0 handshake — and callers time out well before that.
        So a snapshot answers with the last frame this camera produced and lets
        the session come up behind it; only the first snapshot after a restart
        has to wait at all.
        """
        del width, height
        await self._async_ensure_streaming()
        self._schedule_idle_shutdown()
        stream = self.camera_stream
        if stream.last_frame is not None:
            return stream.last_frame
        return await stream.async_wait_for_frame(SNAPSHOT_WARMUP_SECONDS)

    async def handle_async_mjpeg_stream(
        self, request: web.Request
    ) -> web.StreamResponse:
        """
        Serve the camera as multipart MJPEG, pushed as the frames arrive.

        Frames are written as the device produces them rather than polled at a
        fixed rate, so a viewer sees every frame this camera sends and nothing
        is duplicated in between.
        """
        await self._async_ensure_streaming()
        response = web.StreamResponse(
            headers={
                "Content-Type": f"multipart/x-mixed-replace; boundary={MJPEG_BOUNDARY}",
                "Cache-Control": "no-cache",
            }
        )
        await response.prepare(request)
        try:
            async for frame in self.camera_stream.async_frames():
                await response.write((_PART_HEADER % len(frame)).encode())
                await response.write(frame)
                await response.write(b"\r\n")
        except TimeoutError, ConnectionResetError, ConnectionError:
            LOGGER.debug("An MJPEG viewer of %s went away", self._device_id)
        except asyncio.CancelledError:
            raise
        finally:
            self._schedule_idle_shutdown()
        return response

    async def async_added_to_hass(self) -> None:
        """Start reporting the stream's state, and hold it open if asked to."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.camera_stream.add_state_listener(self._on_stream_state)
        )
        if self.keep_connected:
            await self.camera_stream.async_start()

    async def async_will_remove_from_hass(self) -> None:
        """Drop any pending idle shutdown; the entry teardown stops the stream."""
        self._cancel_pending_idle_shutdown()
        await super().async_will_remove_from_hass()

    def _on_stream_state(self) -> None:
        """Write the new state whenever the stream reports a change."""
        self.async_write_ha_state()

    async def _async_ensure_streaming(self) -> None:
        """Bring the session up if it is not already running."""
        self._cancel_pending_idle_shutdown()
        if not self.camera_stream.running:
            LOGGER.debug("Bringing up the session for %s on demand", self._device_id)
            await self.camera_stream.async_start()

    def _schedule_idle_shutdown(self) -> None:
        """
        Release the camera once nothing is watching it.

        A viewer still reading the MJPEG stream keeps the session alive; the
        check runs again while one is connected.
        """
        if self.keep_connected:
            return
        self._cancel_pending_idle_shutdown()
        self._cancel_idle_shutdown = async_call_later(
            self.hass, IDLE_SHUTDOWN_SECONDS, self._on_idle_deadline
        )

    def _cancel_pending_idle_shutdown(self) -> None:
        """Drop a scheduled shutdown, if one is armed."""
        cancel = self._cancel_idle_shutdown
        self._cancel_idle_shutdown = None
        if cancel is not None:
            cancel()

    async def _on_idle_deadline(self, _now: object) -> None:
        """Stop the stream, unless somebody is still watching it."""
        self._cancel_idle_shutdown = None
        if self.camera_stream.viewer_count:
            self._schedule_idle_shutdown()
            return
        LOGGER.debug("No viewers left; releasing the session for %s", self._device_id)
        with contextlib.suppress(Exception):
            await self.camera_stream.async_stop()
