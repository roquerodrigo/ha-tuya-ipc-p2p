"""Repair issues raised for a camera Home Assistant cannot bring back on its own."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import issue_registry

from .const import DOMAIN

if TYPE_CHECKING:
    from collections.abc import Iterable

    from homeassistant.core import HomeAssistant

    from .data import TuyaIpcP2pConfigEntry

ISSUE_NEEDS_POWER_CYCLE = "needs_power_cycle"


def async_review_camera_power_state(
    hass: HomeAssistant,
    entry: TuyaIpcP2pConfigEntry,
    device_id: str,
    camera_name: str,
    *,
    needs_power_cycle: bool,
) -> None:
    """
    Report a camera that stopped answering, and withdraw it when it answers again.

    Nothing Home Assistant does clears this one: the camera turns every offer
    down as busy, the vendor app cannot load it either, and it stays that way
    until someone unplugs it. Left in the log it looks like an ordinary retry.
    """
    issue_id = _issue_id(entry, device_id)
    if not needs_power_cycle:
        issue_registry.async_delete_issue(hass, DOMAIN, issue_id)
        return
    issue_registry.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=issue_registry.IssueSeverity.WARNING,
        translation_key=ISSUE_NEEDS_POWER_CYCLE,
        translation_placeholders={"camera": camera_name},
    )


def async_clear_camera_issues(
    hass: HomeAssistant, entry: TuyaIpcP2pConfigEntry, device_ids: Iterable[str]
) -> None:
    """Withdraw every issue raised for cameras that are going away."""
    for device_id in device_ids:
        issue_registry.async_delete_issue(hass, DOMAIN, _issue_id(entry, device_id))


def _issue_id(entry: TuyaIpcP2pConfigEntry, device_id: str) -> str:
    """Return the issue id one camera of one entry answers to."""
    return f"{entry.entry_id}_{device_id}_{ISSUE_NEEDS_POWER_CYCLE}"
