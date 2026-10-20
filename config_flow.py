"""Config flow."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import CONF_TEMP_ENTITY, DOMAIN


def _schema(default=vol.UNDEFINED) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_TEMP_ENTITY, default=default): EntitySelector(
            EntitySelectorConfig(domain=["sensor", "weather"]))
    })


class GardenConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Garden Tracker", data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema())

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GardenOptionsFlow()


class GardenOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(
            CONF_TEMP_ENTITY, self.config_entry.data[CONF_TEMP_ENTITY])
        return self.async_show_form(step_id="init", data_schema=_schema(current))
