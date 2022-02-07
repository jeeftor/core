"""Config flow for IntelliFire integration."""
from __future__ import annotations

from typing import Any

from aiohttp import ClientConnectionError
from intellifire4py import IntellifireAsync
from intellifire4py import IntellifireControlAsync
import voluptuous as vol
from intellifire4py.control import LoginException

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required("username"): str,
        vol.Required("password"): str
    }
)


async def validate_host_input(hass: HomeAssistant, host: str) -> str:
    """Validate the user input allows us to connect.

      Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
      """
    api = IntellifireAsync(host)
    await api.poll()

    # Return the serial number which will be used to calculate a unique ID for the device/sensors
    return api.data.serial


async def validate_api_access(hass: HomeAssistant, host: str, username: str, password: str):
    ift_control = IntellifireControlAsync(fireplace_ip=host)
    try:
        await ift_control.login(username=username, password=password)
    finally:
        await ift_control.close()


class IntellifireConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IntelliFire."""

    VERSION = 2

    # @staticmethod
    # @callback
    # def async_get_options_flow(config_entry):
    #     """Get the options flow for this handler."""
    #     return IntellifireConfigFlow(config_entry)

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA
            )
        errors = {}

        try:
            serial = await validate_host_input(self.hass, user_input[CONF_HOST])
            # If we don't throw an error everything is peachy!
            await validate_api_access(self.hass,
                                      user_input[CONF_HOST],
                                      user_input[CONF_USERNAME],
                                      user_input[CONF_PASSWORD])
        except (ConnectionError, ClientConnectionError):
            errors["base"] = "cannot_connect"
        except LoginException:
            errors["base"] = "api_error"
        else:
            await self.async_set_unique_id(serial)
            self._abort_if_unique_id_configured(
                updates={CONF_HOST: user_input[CONF_HOST]}
            )

            return self.async_create_entry(
                title="Fireplace",
                data={CONF_HOST: user_input[CONF_HOST]},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors
        )
