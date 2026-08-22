"""Typed shape of the options writable by the options flow."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class TuyaIpcP2pOptionsData(TypedDict, total=False):
    """Shape of the options writable by the options flow."""

    scan_interval: NotRequired[int]
    keep_connected: NotRequired[bool]
    motion_sensitivity: NotRequired[float]
