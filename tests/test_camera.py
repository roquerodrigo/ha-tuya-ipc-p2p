from __future__ import annotations

import copy
from unittest.mock import AsyncMock

from homeassistant.components.camera import async_get_image
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.tuya_ipc_p2p.const import DOMAIN, IDLE_SHUTDOWN_SECONDS
from tests.doubles import DEVICE_ID, ENTRY_DATA, JPEG

ENTITY_ID = "camera.feeder"


async def test_the_camera_entity_is_named_after_the_device(hass, setup_integration):
    entry = er.async_get(hass).async_get(ENTITY_ID)
    assert entry is not None
    assert entry.unique_id == f"{DEVICE_ID}_camera"


async def test_keep_connected_brings_the_session_up_at_setup(
    hass, setup_integration, camera_stream
):
    assert camera_stream.start_calls == 1
    assert camera_stream.running is True


async def test_a_snapshot_returns_the_last_frame(
    hass, setup_integration, camera_stream
):
    camera_stream.deliver(JPEG)
    image = await async_get_image(hass, ENTITY_ID)
    assert image.content == JPEG


async def test_a_snapshot_waits_for_a_cold_session(
    hass, setup_integration, camera_stream
):
    camera_stream.async_wait_for_frame = AsyncMock(return_value=JPEG)
    image = await async_get_image(hass, ENTITY_ID)
    assert image.content == JPEG
    camera_stream.async_wait_for_frame.assert_awaited()


async def test_the_mjpeg_endpoint_writes_every_frame_it_is_given(
    hass, setup_integration, camera_stream, hass_client
):
    camera_stream.frames = [b"first-frame", b"second-frame"]
    client = await hass_client()
    response = await client.get(f"/api/camera_proxy_stream/{ENTITY_ID}")
    assert response.status == 200
    assert "multipart/x-mixed-replace" in response.headers["Content-Type"]
    body = await response.read()
    assert b"first-frame" in body
    assert b"second-frame" in body
    assert body.count(b"Content-Type: image/jpeg") == 2


async def test_a_viewer_that_goes_away_does_not_fail_the_stream(
    hass, setup_integration, camera_stream, hass_client
):
    async def failing_frames():
        yield b"one"
        raise ConnectionResetError

    camera_stream.async_frames = failing_frames
    client = await hass_client()
    response = await client.get(f"/api/camera_proxy_stream/{ENTITY_ID}")
    assert response.status == 200
    assert b"one" in await response.read()


async def test_the_stream_state_is_written_when_the_stream_changes(
    hass, setup_integration, camera_stream
):
    assert hass.states.get(ENTITY_ID).state == "idle"
    camera_stream.deliver(JPEG)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "streaming"


async def test_a_camera_the_account_reports_offline_is_unavailable(
    hass, setup_integration, mock_api_client, camera_stream
):
    mock_api_client.async_camera_states = AsyncMock(
        return_value={
            DEVICE_ID: {"name": "Feeder", "online": False, "local_key": "key"}
        }
    )
    await setup_integration.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "unavailable"


async def test_on_demand_starts_the_session_only_when_something_asks(
    hass, mock_api_client, streams, enable_custom_integrations
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=copy.deepcopy(ENTRY_DATA),
        options={"keep_connected": False},
        unique_id="user_example_com",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    stream = streams[DEVICE_ID]
    assert stream.start_calls == 0

    stream.last_frame = JPEG
    await async_get_image(hass, ENTITY_ID)
    assert stream.start_calls == 1


async def test_on_demand_releases_the_session_once_nobody_is_watching(
    hass, mock_api_client, streams, enable_custom_integrations
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=copy.deepcopy(ENTRY_DATA),
        options={"keep_connected": False},
        unique_id="user_example_com",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    stream = streams[DEVICE_ID]
    stream.last_frame = JPEG
    await async_get_image(hass, ENTITY_ID)
    assert stream.running is True

    async_fire_time_changed(
        hass, dt_util.utcnow() + dt_util.dt.timedelta(seconds=IDLE_SHUTDOWN_SECONDS + 1)
    )
    await hass.async_block_till_done()
    assert stream.stop_calls >= 1


async def test_keep_connected_never_schedules_an_idle_shutdown(
    hass, setup_integration, camera_stream
):
    camera_stream.deliver(JPEG)
    await async_get_image(hass, ENTITY_ID)
    async_fire_time_changed(
        hass, dt_util.utcnow() + dt_util.dt.timedelta(seconds=IDLE_SHUTDOWN_SECONDS + 1)
    )
    await hass.async_block_till_done()
    assert camera_stream.stop_calls == 0


async def test_a_viewer_still_watching_defers_the_idle_shutdown(
    hass, mock_api_client, streams, enable_custom_integrations
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=copy.deepcopy(ENTRY_DATA),
        options={"keep_connected": False},
        unique_id="user_example_com",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    stream = streams[DEVICE_ID]
    stream.last_frame = JPEG
    await async_get_image(hass, ENTITY_ID)
    stream.viewer_count = 1

    async_fire_time_changed(
        hass, dt_util.utcnow() + dt_util.dt.timedelta(seconds=IDLE_SHUTDOWN_SECONDS + 1)
    )
    await hass.async_block_till_done()
    assert stream.stop_calls == 0
    assert stream.running is True


async def test_the_camera_offers_a_stream_source_for_ffmpeg_consumers(
    hass, setup_integration, camera_stream, socket_enabled
):
    from homeassistant.components.camera import (
        CameraEntityFeature,
        async_get_stream_source,
    )

    state = hass.states.get(ENTITY_ID)
    assert state.attributes["supported_features"] & CameraEntityFeature.STREAM

    camera_stream.deliver(JPEG)
    source = await async_get_stream_source(hass, ENTITY_ID)
    assert source is not None
    assert source.startswith("http://127.0.0.1:")


async def test_asking_for_a_stream_source_brings_the_session_up(
    hass, mock_api_client, streams, enable_custom_integrations, socket_enabled
):
    from homeassistant.components.camera import async_get_stream_source

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=copy.deepcopy(ENTRY_DATA),
        options={"keep_connected": False},
        unique_id="user_example_com",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    stream = streams[DEVICE_ID]
    assert stream.start_calls == 0
    await async_get_stream_source(hass, ENTITY_ID)
    assert stream.start_calls == 1
