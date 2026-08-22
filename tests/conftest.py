from __future__ import annotations

import copy
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
