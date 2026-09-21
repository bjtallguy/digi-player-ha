"""Config flow: host, port and token, validated against the live daemon."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DigiPlayerAuthError, DigiPlayerClient, DigiPlayerError
from .const import COMMAND_TIMEOUT_SECONDS, DEFAULT_PORT, DOMAIN


class DigiPlayerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add one digi-player appliance."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            # Prove the daemon answers with this token before storing it, so a
            # typo surfaces here rather than as a permanently broken entity.
            client = DigiPlayerClient(
                async_get_clientsession(self.hass),
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_TOKEN],
            )
            try:
                await client.get_state(COMMAND_TIMEOUT_SECONDS)
            except DigiPlayerAuthError:
                errors["base"] = "invalid_auth"
            except DigiPlayerError:
                errors["base"] = "cannot_connect"
            else:
                unique = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                await self.async_set_unique_id(unique)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or unique,
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_TOKEN: user_input[CONF_TOKEN],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_TOKEN): str,
                vol.Optional(CONF_NAME, default="SR250"): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )
