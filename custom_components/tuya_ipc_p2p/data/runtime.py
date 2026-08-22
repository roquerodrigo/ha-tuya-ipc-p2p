"""Runtime data stored on entry.runtime_data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.loader import Integration
    from tuya_ipc_p2p_sdk import CameraStream

    from ..api import TuyaIpcP2pApiClient
    from ..coordinator import TuyaIpcP2pDataUpdateCoordinator
    from ..stream_server import TuyaIpcP2pStreamServer


@dataclass
class TuyaIpcP2pData:
    """
    Data stored on entry.runtime_data for Tuya IPC P2P.

    ``streams`` holds one supervised stream per configured camera, keyed by
    device id. They live here rather than on the entities because the camera
    and the motion sensor of one device read the same stream, and the stream
    server serves all of them on one loopback port.
    """

    client: TuyaIpcP2pApiClient
    coordinator: TuyaIpcP2pDataUpdateCoordinator
    integration: Integration
    stream_server: TuyaIpcP2pStreamServer
    streams: dict[str, CameraStream] = field(default_factory=dict)
