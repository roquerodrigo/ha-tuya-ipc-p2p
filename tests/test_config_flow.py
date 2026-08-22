from __future__ import annotations

import copy
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tuya_ipc_p2p.const import DOMAIN
from custom_components.tuya_ipc_p2p.exceptions import (
    TuyaIpcP2pApiClientAuthenticationError,
    TuyaIpcP2pApiClientCommunicationError,
    TuyaIpcP2pApiClientError,
)
from tests.doubles import DEVICE_ID, ENTRY_DATA

USER_INPUT = {
    "email": "user@example.com",
    "password": "hunter2",
    "country_code": "55",
    "region": "us",
}
NEW_INPUT = {**USER_INPUT, "password": "new-password"}
DISCOVERED = [
    {"device_id": DEVICE_ID, "name": "Feeder", "local_key": "0123456789abcdef"}
]


@contextmanager
def _patched_client(*, verify_error=None, cameras=None):
    with patch(
        "custom_components.tuya_ipc_p2p.config_flow.TuyaIpcP2pApiClient"
    ) as mock_class:
        instance = mock_class.return_value
        instance.async_verify_credentials = AsyncMock(side_effect=verify_error)
        instance.async_discover_cameras = AsyncMock(
            return_value=copy.deepcopy(DISCOVERED if cameras is None else cameras)
        )
        yield instance


@pytest.fixture
def api_client():
    with _patched_client() as instance:
        yield instance


async def _start_user_flow(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_step_user_shows_form(hass, enable_custom_integrations):
    result = await _start_user_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_step_user_success_persists_the_account_and_its_cameras(
    hass, api_client, enable_custom_integrations
):
    flow = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], user_input=USER_INPUT
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "user@example.com"
    assert result["data"]["email"] == "user@example.com"
    assert result["data"]["region"] == "us"
    assert result["data"]["cameras"] == DISCOVERED


async def test_step_user_success_sets_unique_id(
    hass, api_client, enable_custom_integrations
):
    flow = await _start_user_flow(hass)
    await hass.config_entries.flow.async_configure(
        flow["flow_id"], user_input=USER_INPUT
    )
    assert hass.config_entries.async_entries(DOMAIN)[0].unique_id == "user_example_com"


async def test_step_user_duplicate_aborts(hass, api_client, enable_custom_integrations):
    first = await _start_user_flow(hass)
    await hass.config_entries.flow.async_configure(
        first["flow_id"], user_input=USER_INPUT
    )
    second = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        second["flow_id"], user_input=USER_INPUT
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_step_user_without_a_camera_says_so(hass, enable_custom_integrations):
    with _patched_client(cameras=[]):
        flow = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], user_input=USER_INPUT
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "no_cameras"


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TuyaIpcP2pApiClientAuthenticationError("bad"), "auth"),
        (TuyaIpcP2pApiClientCommunicationError("down"), "connection"),
        (TuyaIpcP2pApiClientError("oops"), "unknown"),
    ],
)
async def test_step_user_maps_failures_onto_form_errors(
    hass, enable_custom_integrations, error, expected
):
    with _patched_client(verify_error=error):
        flow = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], user_input=USER_INPUT
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == expected


def _existing_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data=copy.deepcopy(ENTRY_DATA), unique_id="user_example_com"
    )
    entry.add_to_hass(hass)
    return entry


async def test_reauth_shows_confirm_form(hass, enable_custom_integrations):
    entry = _existing_entry(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"


async def test_reauth_updates_the_password_and_keeps_the_cameras(
    hass, api_client, enable_custom_integrations
):
    entry = _existing_entry(hass)
    flow = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], user_input=NEW_INPUT
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["password"] == "new-password"
    assert entry.data["cameras"] == ENTRY_DATA["cameras"]


async def test_reauth_does_not_rediscover(hass, enable_custom_integrations):
    with _patched_client() as instance:
        entry = _existing_entry(hass)
        flow = await entry.start_reauth_flow(hass)
        await hass.config_entries.flow.async_configure(
            flow["flow_id"], user_input=NEW_INPUT
        )
        instance.async_discover_cameras.assert_not_awaited()


async def test_reauth_with_another_account_aborts(
    hass, api_client, enable_custom_integrations
):
    entry = _existing_entry(hass)
    flow = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], user_input={**USER_INPUT, "email": "someone@example.com"}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
    assert entry.data["email"] == "user@example.com"


async def test_reauth_auth_error_shows_auth(hass, enable_custom_integrations):
    with _patched_client(verify_error=TuyaIpcP2pApiClientAuthenticationError("no")):
        entry = _existing_entry(hass)
        flow = await entry.start_reauth_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], user_input=NEW_INPUT
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "auth"


async def test_reconfigure_refreshes_the_camera_list(hass, enable_custom_integrations):
    replacement = [{"device_id": "another", "name": "Doorbell", "local_key": "key"}]
    with _patched_client(cameras=replacement):
        entry = _existing_entry(hass)
        flow = await entry.start_reconfigure_flow(hass)
        assert flow["step_id"] == "reconfigure"
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], user_input=USER_INPUT
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["cameras"] == replacement


async def test_reconfigure_with_another_account_aborts(
    hass, api_client, enable_custom_integrations
):
    entry = _existing_entry(hass)
    flow = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], user_input={**USER_INPUT, "email": "someone@example.com"}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
