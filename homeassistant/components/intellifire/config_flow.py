"""Config flow for IntelliFire integration."""
from __future__ import annotations

from typing import Any

from aiohttp import ClientConnectionError
from intellifire4py import IntellifireAsync
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.dhcp import DhcpServiceInfo
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, LOGGER


async def validate_input(hass: HomeAssistant, host: str) -> str:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    api = IntellifireAsync(host)
    await api.poll()

    # Return the serial number which will be used to calculate a unique ID for the device/sensors
    return api.data.serial


async def validate_host_input(host: str) -> str:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    api = IntellifireAsync(host)
    await api.poll()
    ret = api.data.serial
    LOGGER.info("Found a fireplace: %s", ret)
    # Return the serial number which will be used to calculate a unique ID for the device/sensors
    return ret


STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


class IntellifireConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IntelliFire."""

    VERSION = 1

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> FlowResult:
        """Handle DHCP Discovery."""
        potential_host = discovery_info.ip

        try:
            serial = await validate_host_input(potential_host)
        except (ConnectionError, ClientConnectionError):
            return self.async_abort(reason="not_intellifire_device")

        await self.async_set_unique_id(serial)
        # check if found before
        self._abort_if_unique_id_configured(
            updates={
                CONF_HOST: potential_host,
            }
        )

        return await self.async_step_user()

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
            serial = await validate_input(self.hass, user_input[CONF_HOST])
        except (ConnectionError, ClientConnectionError):
            errors["base"] = "cannot_connect"
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
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
