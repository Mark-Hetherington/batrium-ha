"""Config flow for Batrium BMS integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_UDP_PORT, DEFAULT_UDP_PORT, DOMAIN


class BatriumConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Batrium."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(f"batrium_{user_input[CONF_UDP_PORT]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, "Batrium BMS"),
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default="Batrium BMS"): str,
                vol.Optional(CONF_UDP_PORT, default=DEFAULT_UDP_PORT): vol.All(
                    int, vol.Range(min=1024, max=65535)
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
