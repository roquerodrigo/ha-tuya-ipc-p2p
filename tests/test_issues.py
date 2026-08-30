"""A camera that has stopped answering is reported where the user looks."""

from __future__ import annotations

import pytest
from homeassistant.helpers import issue_registry

from custom_components.tuya_ipc_p2p.const import DOMAIN
from custom_components.tuya_ipc_p2p.issues import ISSUE_NEEDS_POWER_CYCLE
from tests.doubles import DEVICE_ID


def _issue(hass, entry):
    return issue_registry.async_get(hass).async_get_issue(
        DOMAIN, f"{entry.entry_id}_{DEVICE_ID}_{ISSUE_NEEDS_POWER_CYCLE}"
    )


async def test_a_camera_that_needs_a_power_cycle_raises_an_issue(
    hass, setup_integration, camera_stream
):
    camera_stream.needs_power_cycle = True
    camera_stream.notify()
    await hass.async_block_till_done()

    issue = _issue(hass, setup_integration)
    assert issue is not None
    assert issue.translation_placeholders == {"camera": "Feeder"}


async def test_a_camera_that_answers_again_withdraws_the_issue(
    hass, setup_integration, camera_stream
):
    camera_stream.needs_power_cycle = True
    camera_stream.notify()
    await hass.async_block_till_done()

    camera_stream.needs_power_cycle = False
    camera_stream.notify()
    await hass.async_block_till_done()

    assert _issue(hass, setup_integration) is None


async def test_an_ordinary_state_change_raises_nothing(
    hass, setup_integration, camera_stream
):
    """The stream reports frames and motion through the very same callback."""
    camera_stream.motion_detected = True
    camera_stream.notify()
    await hass.async_block_till_done()

    assert _issue(hass, setup_integration) is None


async def test_unloading_the_entry_withdraws_the_issue(
    hass, setup_integration, camera_stream
):
    camera_stream.needs_power_cycle = True
    camera_stream.notify()
    await hass.async_block_till_done()

    await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()

    assert _issue(hass, setup_integration) is None


@pytest.mark.parametrize("language", ["en", "pt-BR"])
def test_the_issue_is_translated(language):
    import json
    from pathlib import Path

    translations = json.loads(
        (
            Path(__file__).parent.parent
            / "custom_components"
            / "tuya_ipc_p2p"
            / "translations"
            / f"{language}.json"
        ).read_text(encoding="utf-8")
    )
    assert ISSUE_NEEDS_POWER_CYCLE in translations["issues"]
