from __future__ import annotations

from unittest.mock import AsyncMock

from homeassistant.helpers import entity_registry as er

from tests.doubles import DEVICE_ID, JPEG

ENTITY_ID = "binary_sensor.feeder_motion"


async def test_the_motion_sensor_is_registered_per_camera(hass, setup_integration):
    entry = er.async_get(hass).async_get(ENTITY_ID)
    assert entry is not None
    assert entry.unique_id == f"{DEVICE_ID}_motion"
    assert entry.translation_key == "motion"


async def test_motion_is_unavailable_while_no_frames_arrive(hass, setup_integration):
    assert hass.states.get(ENTITY_ID).state == "unavailable"


async def test_motion_follows_the_stream(hass, setup_integration, camera_stream):
    camera_stream.deliver(JPEG)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "off"

    camera_stream.motion_detected = True
    camera_stream.notify()
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "on"

    camera_stream.motion_detected = False
    camera_stream.notify()
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "off"


async def test_motion_goes_unavailable_when_the_camera_does(
    hass, setup_integration, camera_stream, mock_api_client
):
    camera_stream.deliver(JPEG)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "off"

    mock_api_client.async_camera_states = AsyncMock(
        return_value={
            DEVICE_ID: {"name": "Feeder", "online": False, "local_key": "key"}
        }
    )
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "unavailable"


async def test_the_device_carries_the_camera_name(hass, setup_integration):
    from homeassistant.helpers import device_registry as dr

    from custom_components.tuya_ipc_p2p.const import DOMAIN, MANUFACTURER

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, DEVICE_ID)})
    assert device is not None
    assert device.name == "Feeder"
    assert device.manufacturer == MANUFACTURER
    assert device.serial_number == DEVICE_ID
