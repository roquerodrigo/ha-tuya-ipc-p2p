"""Typed shape of the account persisted on the config entry."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from .camera_config import TuyaIpcP2pCameraConfig


class TuyaIpcP2pConfigData(TypedDict):
    """
    Shape of the account persisted on the config entry.

    The camera list is persisted rather than rediscovered on every setup:
    discovery probes the IPC config API once per device on the account, which
    is too heavy to run on a restart. Re-running the flow's reconfigure step
    refreshes it.
    """

    email: str
    password: str
    country_code: str
    region: str
    cameras: list[TuyaIpcP2pCameraConfig]
