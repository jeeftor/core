"""Config flow for IntelliFire integration."""
from __future__ import annotations

# FOR TESTING ONLY REMOVE FROM PRODUCTION
import os
from typing import Any

from aiohttp import ClientConnectionError
from intellifire4py import IntellifireAsync, IntellifireControlAsync
from intellifire4py.control import LoginException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

h = os.getenv("IFT_HOST")
u = os.getenv("IFT_USER")
p = os.getenv("IFT_PASS")

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=h): str,
        vol.Required(CONF_USERNAME, default=u): str,
        vol.Required(CONF_PASSWORD, default=p): str,
        vol.Required(CONF_SSL, default=True): bool,
        vol.Required(CONF_VERIFY_SSL, default=True): bool,
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


async def validate_api_access(hass: HomeAssistant, user_input: dict[str, Any]):
    ift_control = IntellifireControlAsync(
        fireplace_ip=user_input[CONF_HOST],
        use_http=(not user_input[CONF_SSL]),
        verify_ssl=user_input[CONF_VERIFY_SSL],
    )
    try:
        await ift_control.login(
            username=user_input[CONF_USERNAME],
            password=user_input[CONF_PASSWORD],
        )
        username = await ift_control.get_username()

    finally:
        await ift_control.close()


class IntellifireConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IntelliFire."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )
        errors = {}

        try:
            serial = await validate_host_input(self.hass, user_input[CONF_HOST])
            # If we don't throw an error everything is peachy!
            await validate_api_access(self.hass, user_input)
        except (ConnectionError, ClientConnectionError) as error:
            if error.args[0].host == "iftapi.net":
                errors["base"] = "iftapi_connect"
            else:
                errors["base"] = "cannot_connect"
        except LoginException:
            errors["base"] = "api_error"
        except Exception as ex:
            print(ex)
        else:
            await self.async_set_unique_id(serial)
            self._abort_if_unique_id_configured(
                updates={
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_SSL: user_input[CONF_SSL],
                    CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                }
            )
            return self.async_create_entry(
                title="Fireplace",
                data={
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_SSL: user_input[CONF_SSL],
                    CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                },
            )
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
