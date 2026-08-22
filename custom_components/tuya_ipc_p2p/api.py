"""Tuya IPC P2P API client, wrapping the SDK for Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tuya_ipc_p2p_sdk import (
    TuyaIpcP2pAuthenticationError,
    TuyaIpcP2pClient,
    TuyaIpcP2pConnectionError,
    TuyaIpcP2pError,
)

from .exceptions import (
    TuyaIpcP2pApiClientAuthenticationError,
    TuyaIpcP2pApiClientCommunicationError,
    TuyaIpcP2pApiClientError,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable

    import aiohttp
    from tuya_ipc_p2p_sdk import CameraStream, TuyaDevice

    from .data import TuyaIpcP2pCameraConfig, TuyaIpcP2pCameraState


class TuyaIpcP2pApiClient:
    """
    Talks to the Tuya cloud on behalf of one account.

    Everything the SDK raises is translated here, so nothing above this
    boundary ever catches an SDK type.
    """

    def __init__(
        self,
        email: str,
        password: str,
        country_code: str,
        region: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Build the SDK client for one account."""
        self._client = TuyaIpcP2pClient(
            email=email,
            password=password,
            country_code=country_code,
            region=region,
            session=session,
        )

    async def async_verify_credentials(self) -> None:
        """Prove the credentials work, by logging in for real."""
        await self._async_guarded(self._client.async_login())

    async def async_discover_cameras(self) -> list[TuyaIpcP2pCameraConfig]:
        """
        Return the account's devices that this integration can stream.

        Only a camera answers the IPC config API, so the API itself is the
        filter — a device that answers it is one the P2P path works against.
        """
        cameras = await self._async_guarded(self._client.async_discover_cameras())
        return [
            {
                "device_id": camera.device_id,
                "name": camera.name,
                "local_key": camera.local_key,
            }
            for camera in cameras
        ]

    async def async_camera_states(
        self, device_ids: frozenset[str]
    ) -> dict[str, TuyaIpcP2pCameraState]:
        """
        Return what the account's device list says about the configured cameras.

        This is the cheap poll: it lists the account's devices and never probes
        the IPC config API, so it can run on every refresh without minting a
        cloud session for every device on the account.
        """
        devices: list[TuyaDevice] = await self._async_guarded(
            self._client.async_list_devices(),
        )
        return {
            device.device_id: {
                "name": device.name,
                "online": device.online,
                "local_key": device.local_key,
            }
            for device in devices
            if device.device_id in device_ids
        }

    def create_stream(
        self, device_id: str, local_key: str, motion_sensitivity: float
    ) -> CameraStream:
        """Build a supervised stream for one camera; nothing connects until start."""
        return self._client.create_camera_stream(
            device_id=device_id,
            local_key=local_key,
            motion_sensitivity=motion_sensitivity,
        )

    async def async_close(self) -> None:
        """Release whatever the SDK client owns."""
        await self._client.async_close()

    async def _async_guarded[ResultT](self, call: Awaitable[ResultT]) -> ResultT:
        """Await one SDK call, translating its errors into this integration's."""
        try:
            return await call
        except TuyaIpcP2pAuthenticationError as exception:
            message = f"Failed to authenticate: {exception}"
            raise TuyaIpcP2pApiClientAuthenticationError(message) from exception
        except TuyaIpcP2pConnectionError as exception:
            message = f"Failed to reach the Tuya cloud: {exception}"
            raise TuyaIpcP2pApiClientCommunicationError(message) from exception
        except TuyaIpcP2pError as exception:
            message = f"Failed to talk to the Tuya cloud: {exception}"
            raise TuyaIpcP2pApiClientError(message) from exception
