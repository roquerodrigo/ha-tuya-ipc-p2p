"""A loopback server that hands this camera to ffmpeg-based consumers as H.264."""

from __future__ import annotations

import asyncio
import contextlib
import secrets
from typing import TYPE_CHECKING

from aiohttp import web

from .const import LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from tuya_ipc_p2p_sdk import CameraStream

# The camera sends a couple of frames a second and a JPEG sequence carries no
# timestamps, so an encoder times the frames off its own assumed rate and
# stream time advances several times faster than the clock. Feeding the latest
# frame at a fixed cadence — repeating it whenever the camera goes quiet —
# gives the encoder presentation times that match the times frames really have.
OUTPUT_FRAME_RATE = 10
_FRAME_INTERVAL_SECONDS = 1 / OUTPUT_FRAME_RATE

# Keyframes every two seconds, so a consumer that joins mid-stream starts
# decoding quickly and Home Assistant can cut HLS segments.
_KEYFRAME_INTERVAL_SECONDS = 2

# How long a consumer waits for the first frame of a cold session before the
# server gives up on it.
_WARMUP_SECONDS = 45

_READ_CHUNK_BYTES = 65536
_SHUTDOWN_GRACE_SECONDS = 2


def encoder_arguments() -> list[str]:
    """
    Return the ffmpeg arguments that turn the JPEG sequence into MPEG-TS H.264.

    The device only ever produces MJPEG, and every consumer that matters —
    Home Assistant's own HLS pipeline, the HomeKit bridges — needs H.264:
    handing them MJPEG produces a playlist no browser decodes and an accessory
    with nothing to show. Quality per bit is traded for speed because this
    runs alongside everything else on the host.
    """
    return [
        "-hide_banner",
        "-nostats",
        "-loglevel",
        "error",
        "-f",
        "mjpeg",
        "-framerate",
        str(OUTPUT_FRAME_RATE),
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-tune",
        "zerolatency",
        "-profile:v",
        "baseline",
        "-pix_fmt",
        "yuv420p",
        # The camera writes a JFIF density of 640x480 in "aspect ratio" units,
        # which decodes as a pixel aspect ratio of 4:3 — so a 640x480 frame
        # claims to be displayed at 16:9 and every player stretches it. The
        # pixels are square; the header is wrong. Declaring that here is what
        # keeps the picture 4:3, and snapshots never showed the fault because
        # an <img> ignores the field entirely.
        "-vf",
        "setsar=1",
        "-bf",
        "0",
        "-g",
        str(OUTPUT_FRAME_RATE * _KEYFRAME_INTERVAL_SECONDS),
        "-f",
        "mpegts",
        "pipe:1",
    ]


class TuyaIpcP2pStreamServer:
    """
    Serves each camera as H.264 over MPEG-TS on the loopback interface.

    Home Assistant's own consumers reach a camera through the entity, but
    anything built on ffmpeg — the ``stream`` integration, the HomeKit
    bridges — is a separate process that can only be handed a URL. This is
    that URL, and it transcodes because those consumers do not accept MJPEG.

    One encoder runs per connected consumer rather than one shared by all:
    at this camera's resolution and frame rate an encoder costs very little,
    and a consumer that joins late gets its own clean start instead of the
    middle of somebody else's stream.

    It listens on the loopback interface only, and each camera sits behind a
    path token minted per config entry, so the stream is not readable by
    anything that cannot already read this integration's memory.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        streams: dict[str, CameraStream],
        ffmpeg_binary: str,
    ) -> None:
        """Describe the streams to serve; no port is bound until one is asked for."""
        self._hass = hass
        self._streams = streams
        self._ffmpeg_binary = ffmpeg_binary
        self._token = secrets.token_urlsafe(16)
        self._runner: web.AppRunner | None = None
        self._port: int | None = None
        self._lock = asyncio.Lock()

    async def async_url(self, device_id: str) -> str | None:
        """
        Return the URL one camera is served on, binding the port on first use.

        Nothing listens until an ffmpeg consumer actually asks for a source,
        so an installation whose cameras are only ever viewed through Home
        Assistant never opens a port at all.
        """
        if device_id not in self._streams:
            return None
        async with self._lock:
            if self._runner is None:
                await self._async_start()
        if self._port is None:
            return None
        return f"http://127.0.0.1:{self._port}/{self._token}/{device_id}"

    async def _async_start(self) -> None:
        """Bind an ephemeral loopback port and start serving."""
        application = web.Application()
        application.router.add_get("/{token}/{device_id}", self._async_serve)
        runner = web.AppRunner(application)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        self._runner = runner
        self._port = _bound_port(site)
        LOGGER.debug("Serving H.264 for ffmpeg consumers on 127.0.0.1:%s", self._port)

    async def async_stop(self) -> None:
        """Stop serving and release the port, if one was ever bound."""
        async with self._lock:
            runner = self._runner
            self._runner = None
            self._port = None
        if runner is not None:
            await runner.cleanup()

    async def _async_serve(self, request: web.Request) -> web.StreamResponse:
        """Encode one camera for as long as the consumer keeps reading."""
        if request.match_info["token"] != self._token:
            raise web.HTTPNotFound
        stream = self._streams.get(request.match_info["device_id"])
        if stream is None:
            raise web.HTTPNotFound

        if not stream.running:
            await stream.async_start()
        if await stream.async_wait_for_frame(_WARMUP_SECONDS) is None:
            raise web.HTTPServiceUnavailable

        process = await asyncio.create_subprocess_exec(
            self._ffmpeg_binary,
            *encoder_arguments(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        response = web.StreamResponse(
            headers={"Content-Type": "video/mp2t", "Cache-Control": "no-cache"}
        )
        await response.prepare(request)

        feeder = asyncio.create_task(_async_feed_encoder(process, stream))
        try:
            await _async_forward_encoder(process, response)
        finally:
            feeder.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await feeder
            await _async_terminate(process)
        return response


async def _async_feed_encoder(
    process: asyncio.subprocess.Process, stream: CameraStream
) -> None:
    """Write the latest frame to the encoder at a steady cadence."""
    stdin = process.stdin
    if stdin is None:
        return
    with contextlib.suppress(
        BrokenPipeError, ConnectionResetError, asyncio.IncompleteReadError
    ):
        while True:
            frame = stream.last_frame
            if frame is not None:
                stdin.write(frame)
                await stdin.drain()
            await asyncio.sleep(_FRAME_INTERVAL_SECONDS)


async def _async_forward_encoder(
    process: asyncio.subprocess.Process, response: web.StreamResponse
) -> None:
    """Copy the encoder's output to the consumer until either side goes away."""
    stdout = process.stdout
    if stdout is None:
        return
    with contextlib.suppress(
        TimeoutError, ConnectionResetError, ConnectionError, BrokenPipeError
    ):
        while chunk := await stdout.read(_READ_CHUNK_BYTES):
            await response.write(chunk)


async def _async_terminate(process: asyncio.subprocess.Process) -> None:
    """Stop one encoder, killing it if it does not go quietly."""
    if process.returncode is not None:
        return
    with contextlib.suppress(ProcessLookupError):
        process.terminate()
    try:
        async with asyncio.timeout(_SHUTDOWN_GRACE_SECONDS):
            await process.wait()
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            process.kill()
        await process.wait()


def _bound_port(site: web.TCPSite) -> int | None:
    """Read back the ephemeral port aiohttp actually bound."""
    name = site.name
    _, _, port = name.rpartition(":")
    return int(port) if port.isdigit() else None
