from __future__ import annotations

import asyncio

import aiohttp
import pytest

from custom_components.tuya_ipc_p2p.stream_server import (
    OUTPUT_FRAME_RATE,
    encoder_arguments,
)
from tests.doubles import DEVICE_ID, JPEG


async def _read_encoded(
    url: str, wanted_bytes: int, deadline_seconds: float = 30.0
) -> bytes:
    """Read from the loopback server until the encoder has produced enough output."""
    collected = bytearray()
    async with aiohttp.ClientSession() as session, session.get(url) as response:
        assert response.status == 200
        assert response.headers["Content-Type"] == "video/mp2t"
        async with asyncio.timeout(deadline_seconds):
            while len(collected) < wanted_bytes:
                chunk = await response.content.read(4096)
                if not chunk:
                    break
                collected += chunk
    return bytes(collected)


async def test_the_server_publishes_a_url_per_camera(
    hass, setup_integration, stream_server, socket_enabled
):
    url = await stream_server.async_url(DEVICE_ID)
    assert url is not None
    assert url.startswith("http://127.0.0.1:")
    assert DEVICE_ID in url


async def test_an_unknown_camera_has_no_url(hass, setup_integration, stream_server):
    assert await stream_server.async_url("not-a-camera") is None


async def test_the_stream_is_h264_inside_mpeg_ts(
    hass, setup_integration, stream_server, socket_enabled, camera_stream
):
    # Every consumer that matters wants H.264: handing them the camera's own
    # MJPEG produces an HLS playlist no browser decodes.
    camera_stream.deliver(JPEG)
    body = await _read_encoded(await stream_server.async_url(DEVICE_ID), 4096)
    assert body[0] == 0x47, "MPEG-TS packets start with the sync byte"
    assert len(body) % 188 == 0 or len(body) > 188


def test_the_encoder_produces_h264_over_mpeg_ts_at_a_fixed_rate():
    arguments = encoder_arguments()
    assert arguments[arguments.index("-c:v") + 1] == "libx264"
    assert arguments[arguments.index("-f", arguments.index("-c:v")) + 1] == "mpegts"
    assert arguments[arguments.index("-framerate") + 1] == str(OUTPUT_FRAME_RATE)
    # A JPEG sequence carries no timestamps, so the declared input rate is
    # what keeps stream time running at the speed of the clock.
    assert arguments[arguments.index("-i") + 1] == "pipe:0"


async def test_a_wrong_token_is_not_served(
    hass, setup_integration, stream_server, socket_enabled
):
    url = await stream_server.async_url(DEVICE_ID)
    wrong = url.rsplit("/", 2)[0] + f"/not-the-token/{DEVICE_ID}"
    async with aiohttp.ClientSession() as session, session.get(wrong) as response:
        assert response.status == 404


async def test_an_unknown_path_is_not_served(
    hass, setup_integration, stream_server, socket_enabled
):
    url = await stream_server.async_url(DEVICE_ID)
    unknown = url.rsplit("/", 1)[0] + "/not-a-camera"
    async with aiohttp.ClientSession() as session, session.get(unknown) as response:
        assert response.status == 404


async def test_a_camera_that_never_produces_a_frame_is_refused(
    hass, setup_integration, stream_server, socket_enabled, camera_stream, monkeypatch
):
    monkeypatch.setattr(
        "custom_components.tuya_ipc_p2p.stream_server._WARMUP_SECONDS", 0.05
    )

    async def never(_timeout):
        return None

    camera_stream.async_wait_for_frame = never
    async with (
        aiohttp.ClientSession() as session,
        session.get(await stream_server.async_url(DEVICE_ID)) as response,
    ):
        assert response.status == 503


async def test_a_request_brings_a_stopped_session_up(
    hass, setup_integration, stream_server, socket_enabled, camera_stream
):
    await camera_stream.async_stop()
    camera_stream.deliver(JPEG)
    await _read_encoded(await stream_server.async_url(DEVICE_ID), 188)
    assert camera_stream.running is True


async def test_stopping_the_server_releases_the_port(
    hass, setup_integration, stream_server, socket_enabled
):
    url = await stream_server.async_url(DEVICE_ID)
    await stream_server.async_stop()
    with pytest.raises(aiohttp.ClientError):
        async with (
            aiohttp.ClientSession() as session,
            session.get(url, timeout=aiohttp.ClientTimeout(total=5)),
        ):
            pass


async def test_nothing_binds_a_port_until_a_url_is_asked_for(
    hass, setup_integration, stream_server
):
    # The socket guard of the test harness is the assertion: this test does
    # not lift it, so a server that bound eagerly would fail here.
    assert stream_server._runner is None
    assert await stream_server.async_url("not-a-camera") is None
    assert stream_server._runner is None
