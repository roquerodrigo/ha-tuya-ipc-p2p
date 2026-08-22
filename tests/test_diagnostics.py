from __future__ import annotations

from custom_components.tuya_ipc_p2p.diagnostics import (
    async_get_config_entry_diagnostics,
)
from tests.doubles import DEVICE_ID, JPEG


async def test_the_account_is_redacted(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diag["entry"]["data"]["email"] == "**REDACTED**"
    assert diag["entry"]["data"]["password"] == "**REDACTED**"
    assert diag["entry"]["data"]["country_code"] == "**REDACTED**"


async def test_every_camera_local_key_is_redacted(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    for camera in diag["entry"]["data"]["cameras"]:
        assert camera["local_key"] == "**REDACTED**"
    for state in diag["coordinator_data"].values():
        assert state["local_key"] == "**REDACTED**"


async def test_the_entry_metadata_is_included(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diag["entry"]["domain"] == "tuya_ipc_p2p"
    assert diag["entry"]["version"] == 1
    assert "title" in diag["entry"]
    assert isinstance(diag["entry"]["options"], dict)


async def test_the_streams_report_what_they_are_doing(
    hass, setup_integration, camera_stream
):
    camera_stream.deliver(JPEG)
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    stream = diag["streams"][DEVICE_ID]
    assert stream["running"] is True
    assert stream["streaming"] is True
    assert stream["motion_detected"] is False
    assert stream["last_frame_bytes"] == len(JPEG)


async def test_a_stream_with_no_frame_yet_reports_none(hass, setup_integration):
    diag = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert diag["streams"][DEVICE_ID]["last_frame_bytes"] is None
