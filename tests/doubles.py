"""Shared constants and the test double that stands in for an SDK stream."""

from __future__ import annotations

import asyncio

DEVICE_ID = "eb32bf0cd7c898317cxwf9"
LOCAL_KEY = "0123456789abcdef"
JPEG = b"\xff\xd8sample-frame\xff\xd9"

ENTRY_DATA = {
    "email": "user@example.com",
    "password": "hunter2",
    "country_code": "55",
    "region": "us",
    "cameras": [{"device_id": DEVICE_ID, "name": "Feeder", "local_key": LOCAL_KEY}],
}

CAMERA_STATES = {
    DEVICE_ID: {"name": "Feeder", "online": True, "local_key": LOCAL_KEY},
}


class FakeCameraStream:
    """Stands in for the SDK's supervised stream, driven by the tests."""

    def __init__(self, device_id: str, local_key: str, motion_sensitivity: float):
        self.device_id = device_id
        self.local_key = local_key
        self.motion_sensitivity = motion_sensitivity
        self.running = False
        self.streaming = False
        self.motion_detected = False
        self.last_frame: bytes | None = None
        self.viewer_count = 0
        self.start_calls = 0
        self.stop_calls = 0
        self.frames: list[bytes] = []
        self._listeners: list = []

    def add_state_listener(self, listener):
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    def deliver(self, frame: bytes = JPEG) -> None:
        self.last_frame = frame
        self.streaming = True
        self.notify()

    async def async_start(self) -> None:
        self.running = True
        self.start_calls += 1

    async def async_stop(self) -> None:
        self.running = False
        self.streaming = False
        self.stop_calls += 1

    async def async_close(self) -> None:
        await self.async_stop()

    async def async_wait_for_frame(self, timeout_seconds: float) -> bytes | None:
        del timeout_seconds
        return self.last_frame

    async def async_frames(self):
        for frame in self.frames:
            self.viewer_count = 1
            yield frame
        self.viewer_count = 0
        await asyncio.sleep(0)
