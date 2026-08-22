"""Typed shape of one camera as the config entry persists it."""

from __future__ import annotations

from typing import TypedDict


class TuyaIpcP2pCameraConfig(TypedDict):
    """One camera discovered during setup and stored on the config entry."""

    device_id: str
    name: str
    local_key: str
