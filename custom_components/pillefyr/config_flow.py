"""Config flow: Tilføj integration → Stokercloud-login."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import PilleFyrAPI
from .const import DOMAIN


class PilleFyrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Opsæt pillefyr via brugerfladen."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = PilleFyrAPI(
                session, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            try:
                await api.login()
            except Exception:  # network or auth — vi viser generisk fejl
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Pillefyr ({user_input[CONF_USERNAME]})", data=user_input
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )
