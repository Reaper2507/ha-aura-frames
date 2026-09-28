from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AuraApiError
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN


class AuraConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input:
            try:
                api = __import__("custom_components.aura_frames.api", fromlist=["AuraApi"]).AuraApi(
                    async_get_clientsession(self.hass), user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )
                await api.login()
            except (AuraApiError, Exception):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Aura Frames", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return config_entries.OptionsFlow()

