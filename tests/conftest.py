from __future__ import annotations

import copy
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from tests.doubles import CAMERA_STATES, DEVICE_ID, ENTRY_DATA, FakeCameraStream

if TYPE_CHECKING:
    from collections.abc import Generator

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture
def camera_states() -> dict:
    return copy.deepcopy(CAMERA_STATES)


@pytest.fixture
def streams() -> dict[str, FakeCameraStream]:
    return {}


@pytest.fixture
def mock_api_client(camera_states, streams) -> Generator:
    def create_stream(device_id, local_key, motion_sensitivity):
        stream = FakeCameraStream(device_id, local_key, motion_sensitivity)
        streams[device_id] = stream
        return stream

    with patch("custom_components.tuya_ipc_p2p.TuyaIpcP2pApiClient") as mock_class:
        instance = mock_class.return_value
        instance.async_verify_credentials = AsyncMock(return_value=None)
        instance.async_camera_states = AsyncMock(return_value=camera_states)
        instance.async_discover_cameras = AsyncMock(
            return_value=copy.deepcopy(ENTRY_DATA["cameras"])
        )
        instance.async_close = AsyncMock(return_value=None)
        instance.create_stream = create_stream
        yield instance


# An encoder that needs no ffmpeg on the machine running the tests. It records
# its pid so a test can prove the process is reaped, and answers every read of
# its stdin with a chunk that starts like an MPEG-TS packet.
FAKE_ENCODER = """#!/usr/bin/env python3
import os, pathlib, sys

pathlib.Path(__file__ + ".pid").write_text(str(os.getpid()))
out = sys.stdout.buffer
while sys.stdin.buffer.read1(65536):
    out.write(b"\\x47" + bytes(1879))
    out.flush()
"""


@pytest.fixture
def fake_encoder(tmp_path_factory) -> Path:
    """Write the stand-in encoder and return the path to it."""
    path = tmp_path_factory.mktemp("encoder") / "fake-encoder"
    path.write_text(FAKE_ENCODER)
    path.chmod(0o755)
    return path


@pytest.fixture(autouse=True)
def mock_ffmpeg_manager(fake_encoder):
    """Home Assistant resolves the encoder binary through its ffmpeg integration."""
    with patch("custom_components.tuya_ipc_p2p.get_ffmpeg_manager") as manager:
        manager.return_value.binary = str(fake_encoder)
        yield manager


@pytest.fixture
def config_entry(hass):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.tuya_ipc_p2p.const import DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=copy.deepcopy(ENTRY_DATA),
        unique_id="user-example-com",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def setup_integration(
    hass, mock_api_client, config_entry, enable_custom_integrations
):
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture
def camera_stream(streams) -> FakeCameraStream:
    return streams[DEVICE_ID]


@pytest.fixture
def stream_server(setup_integration):
    return setup_integration.runtime_data.stream_server
