from __future__ import annotations

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResultType

from custom_components.tuya_ipc_p2p.const import (
    CONF_KEEP_CONNECTED,
    CONF_MOTION_SENSITIVITY,
    DEFAULT_KEEP_CONNECTED,
    DEFAULT_SCAN_INTERVAL_SECONDS,
)
from custom_components.tuya_ipc_p2p.options_flow import DEFAULT_MOTION_SENSITIVITY


def _default_of(result, key):
    schema = result["data_schema"].schema
    entry = next(item for item in schema if getattr(item, "schema", item) == key)
    return entry.default()


async def test_the_form_offers_every_option_with_its_default(hass, setup_integration):
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert _default_of(result, CONF_SCAN_INTERVAL) == DEFAULT_SCAN_INTERVAL_SECONDS
    assert _default_of(result, CONF_KEEP_CONNECTED) == DEFAULT_KEEP_CONNECTED
    assert _default_of(result, CONF_MOTION_SENSITIVITY) == DEFAULT_MOTION_SENSITIVITY


async def test_the_options_are_persisted(hass, setup_integration):
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: 120,
            CONF_KEEP_CONNECTED: False,
            CONF_MOTION_SENSITIVITY: 3,
        },
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert setup_integration.options[CONF_SCAN_INTERVAL] == 120
    assert setup_integration.options[CONF_KEEP_CONNECTED] is False
    assert setup_integration.options[CONF_MOTION_SENSITIVITY] == 3


async def test_the_stored_values_become_the_defaults(hass, setup_integration):
    hass.config_entries.async_update_entry(
        setup_integration, options={CONF_SCAN_INTERVAL: 180, CONF_KEEP_CONNECTED: False}
    )
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    assert _default_of(result, CONF_SCAN_INTERVAL) == 180
    assert _default_of(result, CONF_KEEP_CONNECTED) is False
