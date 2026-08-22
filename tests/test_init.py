from __future__ import annotations

import copy
from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_SCAN_INTERVAL
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tuya_ipc_p2p import (
    async_reload_entry,
    async_remove_config_entry_device,
)
from custom_components.tuya_ipc_p2p.const import (
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)
from tests.doubles import DEVICE_ID, ENTRY_DATA


async def test_setup_entry_loads_successfully(hass, setup_integration):
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_setup_entry_creates_one_entity_per_platform(hass, setup_integration):
    assert len(hass.states.async_all("camera")) == 1
    assert len(hass.states.async_all("binary_sensor")) == 1


async def test_setup_entry_builds_one_stream_per_camera(
    hass, setup_integration, streams
):
    assert set(setup_integration.runtime_data.streams) == {DEVICE_ID}
    assert streams[DEVICE_ID].local_key == ENTRY_DATA["cameras"][0]["local_key"]


async def test_setup_entry_registers_update_listener(hass, setup_integration):
    assert len(setup_integration.update_listeners) == 1


async def test_unload_entry_stops_every_stream(hass, setup_integration, camera_stream):
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert setup_integration.state == ConfigEntryState.NOT_LOADED
    assert camera_stream.stop_calls >= 1


async def test_unload_entry_closes_the_client(hass, setup_integration, mock_api_client):
    await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    mock_api_client.async_close.assert_awaited()


async def test_reload_entry_restores_loaded_state(hass, setup_integration):
    await async_reload_entry(hass, setup_integration)
    await hass.async_block_till_done()
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_runtime_data_populated(hass, setup_integration):
    assert setup_integration.runtime_data.client is not None
    assert setup_integration.runtime_data.coordinator is not None
    assert setup_integration.runtime_data.integration is not None


async def test_scan_interval_defaults_to_const(hass, setup_integration):
    assert setup_integration.runtime_data.coordinator.update_interval == timedelta(
        seconds=DEFAULT_SCAN_INTERVAL_SECONDS
    )


async def test_scan_interval_picks_up_options(
    hass, mock_api_client, enable_custom_integrations
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=copy.deepcopy(ENTRY_DATA),
        options={CONF_SCAN_INTERVAL: 90},
        unique_id="user-example-com",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.coordinator.update_interval == timedelta(seconds=90)


async def test_motion_sensitivity_reaches_the_stream(
    hass, mock_api_client, streams, enable_custom_integrations
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=copy.deepcopy(ENTRY_DATA),
        options={"motion_sensitivity": 12},
        unique_id="user-example-com",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert streams[DEVICE_ID].motion_sensitivity == 12


async def test_remove_device_refuses_a_camera_the_entry_configures(
    hass, setup_integration
):
    from homeassistant.helpers import device_registry as dr

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, DEVICE_ID)})
    assert device is not None
    assert not await async_remove_config_entry_device(hass, setup_integration, device)


async def test_remove_device_allows_a_camera_the_entry_no_longer_configures(
    hass, setup_integration
):
    from homeassistant.helpers import device_registry as dr

    stale = dr.async_get(hass).async_get_or_create(
        config_entry_id=setup_integration.entry_id,
        identifiers={(DOMAIN, "camera-that-went-away")},
    )
    assert await async_remove_config_entry_device(hass, setup_integration, stale)
