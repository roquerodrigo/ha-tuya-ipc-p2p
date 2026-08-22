"""Options flow for tuya_ipc_p2p."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.config_entries import ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers import selector

from .const import (
    CONF_KEEP_CONNECTED,
    CONF_MOTION_SENSITIVITY,
    DEFAULT_KEEP_CONNECTED,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
)

if TYPE_CHECKING:
    from .data import TuyaIpcP2pOptionsData

DEFAULT_MOTION_SENSITIVITY = 6.0
MIN_MOTION_SENSITIVITY = 1.0
MAX_MOTION_SENSITIVITY = 60.0


class TuyaIpcP2pOptionsFlow(OptionsFlow):
    """Options flow for Tuya IPC P2P."""

    async def async_step_init(
        self,
        user_input: TuyaIpcP2pOptionsData | None = None,
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=dict(user_input))

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_KEEP_CONNECTED,
                        default=options.get(
                            CONF_KEEP_CONNECTED, DEFAULT_KEEP_CONNECTED
                        ),
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_MOTION_SENSITIVITY,
                        default=options.get(
                            CONF_MOTION_SENSITIVITY, DEFAULT_MOTION_SENSITIVITY
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_MOTION_SENSITIVITY,
                            max=MAX_MOTION_SENSITIVITY,
                            step=0.5,
                            mode=selector.NumberSelectorMode.BOX,
                        ),
                    ),
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL_SECONDS,
                            step=10,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        ),
                    ),
                },
            ),
        )
