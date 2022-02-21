"""Config flow for IntelliFire integration."""
from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import ClientConnectionError
from intellifire4py import (
    AsyncUDPFireplaceFinder,
    IntellifireAsync,
    IntellifireControlAsync,
)
from intellifire4py.control import LoginException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.dhcp import DhcpServiceInfo
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, LOGGER


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


async def validate_api_access(user_input: dict[str, Any]):
    """Validate username/password against api."""

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
        await ift_control.get_username()
    finally:
        await ift_control.close()


class IntellifireConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IntelliFire."""

    VERSION = 1

    def __init__(self):
        self._discovered_host: str = ""
        self.fireplace_finder = AsyncUDPFireplaceFinder()

        self._config_context = {CONF_SSL: True, CONF_VERIFY_SSL: True}

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> FlowResult:
        """Handle DHCP Discovery."""
        potential_host = discovery_info.ip
        LOGGER.debug(discovery_info)
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

        self._discovered_host = potential_host
        return await self.async_step_user()

    async def _find_fireplaces(self):
        """Perform UDP discovery."""
        ips = await self.fireplace_finder.search_fireplace(timeout=1)
        if ip := ips[0]:
            self._discovered_host = ip

    async def async_step_local_config(self, user_input=None):
        """Handle local ip configuration."""
        local_schema = vol.Schema(
            {vol.Required(CONF_HOST, default=self._discovered_host): str}
        )
        errors = {}

        if user_input is not None:
            try:
                serial = await validate_host_input(user_input[CONF_HOST])

                await self.async_set_unique_id(serial)

                # Before jumping to next step store the host info in a instance variable
                self._config_context[CONF_HOST] = user_input[CONF_HOST]

                return await self.async_step_api_config(user_input=user_input)

            except (ConnectionError, ClientConnectionError):
                errors["base"] = "cannot_connect"
                return self.async_show_form(
                    step_id="local_config",
                    errors=errors,
                    description_placeholders={CONF_HOST: user_input[CONF_HOST]},
                    data_schema=vol.Schema(
                        {vol.Required(CONF_HOST, default=user_input[CONF_HOST]): str}
                    ),
                )

        return self.async_show_form(
            step_id="local_config", errors=errors, data_schema=local_schema
        )

    async def async_step_api_config(self, user_input: dict[str, Any]):
        """Handle IFTAPI Config options for control."""
        errors = {}
        username = user_input.get(CONF_USERNAME, "")
        password = user_input.get(CONF_PASSWORD, "")

        control_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=username): str,
                vol.Required(CONF_PASSWORD, default=password): str,
            }
        )

        # username / password are required fields - so can check against only one of them
        if username != "":
            try:
                # Update config context & validate
                self._config_context[CONF_USERNAME] = username
                self._config_context[CONF_PASSWORD] = password
                await validate_api_access(user_input=self._config_context)
            except (ConnectionError, ClientConnectionError) as error:
                errors["base"] = "iftapi_connect"
            except LoginException:
                errors["base"] = "api_error"

            return self.async_create_entry(
                title="Fireplace",
                data=self._config_context
                # data={
                #     CONF_HOST: user_input[CONF_HOST],
                #     CONF_USERNAME: user_input[CONF_USERNAME],
                #     CONF_PASSWORD: user_input[CONF_PASSWORD],
                #     CONF_SSL: True,
                #     CONF_VERIFY_SSL: True,
                # }
            )

        return self.async_show_form(step_id="api_config", data_schema=control_schema)

        #
        # if user_input is None:
        #     return self.async_show_form(
        #         step_id="user_local",
        #         data_schema=local_schema
        #     )
        #
        # try:
        #     serial = await validate_input(self.hass, user_input[CONF_HOST])
        # except (ConnectionError, ClientConnectionError):
        #     errors["base"] = "cannot_connect"
        # else:
        #     await self.async_set_unique_id(serial)
        #     self._abort_if_unique_id_configured(
        #         updates={CONF_HOST: user_input[CONF_HOST]}
        #     )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Start the user flow."""

        # If the integration was not triggered by DHCP attempt a quick local discovery
        if self._discovered_host == "":
            await self._find_fireplaces()

        return await self.async_step_local_config()
