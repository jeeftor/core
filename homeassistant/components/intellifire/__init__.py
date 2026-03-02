"""The IntelliFire integration."""

from __future__ import annotations

import asyncio

from intellifire4py import UnifiedFireplace
from intellifire4py.cloud_interface import IntelliFireCloudInterface
from intellifire4py.const import IntelliFireApiMode
from intellifire4py.model import IntelliFireCommonFireplaceData

from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import (
    API_MODE_LOCAL,
    CONF_AUTH_COOKIE,
    CONF_CONTROL_MODE,
    CONF_READ_MODE,
    CONF_SERIAL,
    CONF_USER_ID,
    CONF_WEB_CLIENT_ID,
    INIT_WAIT_TIME_SECONDS,
    LOGGER,
    STARTUP_TIMEOUT,
)
from .coordinator import IntellifireConfigEntry, IntellifireDataUpdateCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.FAN,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


def _construct_common_data(
    entry: IntellifireConfigEntry,
) -> IntelliFireCommonFireplaceData:
    """Convert config entry data into IntelliFireCommonFireplaceData."""

    return IntelliFireCommonFireplaceData(
        auth_cookie=entry.data[CONF_AUTH_COOKIE],
        user_id=entry.data[CONF_USER_ID],
        web_client_id=entry.data[CONF_WEB_CLIENT_ID],
        serial=entry.data[CONF_SERIAL],
        api_key=entry.data[CONF_API_KEY],
        ip_address=entry.data[CONF_IP_ADDRESS],
        read_mode=IntelliFireApiMode(entry.options.get(CONF_READ_MODE, API_MODE_LOCAL)),
        control_mode=IntelliFireApiMode(
            entry.options.get(CONF_CONTROL_MODE, API_MODE_LOCAL)
        ),
    )


async def async_migrate_entry(
    hass: HomeAssistant, config_entry: IntellifireConfigEntry
) -> bool:
    """Migrate entries."""
    LOGGER.debug(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    if config_entry.version == 1:
        new = {**config_entry.data}

        if config_entry.minor_version < 2:
            username = config_entry.data[CONF_USERNAME]
            password = config_entry.data[CONF_PASSWORD]

            # Create a Cloud Interface
            async with IntelliFireCloudInterface() as cloud_interface:
                await cloud_interface.login_with_credentials(
                    username=username, password=password
                )

                new_data = cloud_interface.user_data.get_data_for_ip(new[CONF_HOST])

            if not new_data:
                raise ConfigEntryAuthFailed
            new[CONF_API_KEY] = new_data.api_key
            new[CONF_WEB_CLIENT_ID] = new_data.web_client_id
            new[CONF_AUTH_COOKIE] = new_data.auth_cookie

            new[CONF_IP_ADDRESS] = new_data.ip_address
            new[CONF_SERIAL] = new_data.serial

            hass.config_entries.async_update_entry(
                config_entry,
                data=new,
                options={
                    CONF_READ_MODE: API_MODE_LOCAL,
                    CONF_CONTROL_MODE: API_MODE_LOCAL,
                },
                unique_id=new[CONF_SERIAL],
                version=1,
                minor_version=2,
            )
            LOGGER.debug("Pseudo Migration %s successful", config_entry.version)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: IntellifireConfigEntry) -> bool:
    """Set up IntelliFire from a config entry."""

    if CONF_USERNAME not in entry.data:
        LOGGER.debug("Config entry without username detected: %s", entry.unique_id)
        raise ConfigEntryAuthFailed

    try:
        fireplace: UnifiedFireplace = (
            await UnifiedFireplace.build_fireplace_from_common(
                _construct_common_data(entry)
            )
        )
        LOGGER.debug("Waiting for Fireplace to Initialize")
        await asyncio.wait_for(
            _async_wait_for_initialization(fireplace), timeout=STARTUP_TIMEOUT
        )
    except TimeoutError as err:
        raise ConfigEntryNotReady(
            "Initialization of fireplace timed out after 10 minutes"
        ) from err

    # Check connectivity and apply fallback if needed
    await _async_validate_and_set_modes(fireplace, entry)

    # Construct coordinator
    data_update_coordinator = IntellifireDataUpdateCoordinator(hass, entry, fireplace)

    LOGGER.debug("Fireplace to Initialized - Awaiting first refresh")
    await data_update_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = data_update_coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def _async_validate_and_set_modes(
    fireplace: UnifiedFireplace, entry: IntellifireConfigEntry
) -> None:
    """Validate connectivity and fall back to available mode if preferred is unavailable."""
    await fireplace.async_validate_connectivity()

    local_available = fireplace.local_connectivity
    cloud_available = fireplace.cloud_connectivity

    # Get user's preferred modes
    preferred_read = entry.options.get(CONF_READ_MODE, API_MODE_LOCAL)
    preferred_control = entry.options.get(CONF_CONTROL_MODE, API_MODE_LOCAL)

    # Determine actual read mode with fallback
    if preferred_read == API_MODE_LOCAL:
        if local_available:
            read_mode = IntelliFireApiMode.LOCAL
        elif cloud_available:
            LOGGER.info("Local read unavailable, falling back to cloud")
            read_mode = IntelliFireApiMode.CLOUD
        else:
            raise ConfigEntryNotReady("Neither local nor cloud connectivity available")
    elif cloud_available:
        read_mode = IntelliFireApiMode.CLOUD
    elif local_available:
        LOGGER.info("Cloud read unavailable, falling back to local")
        read_mode = IntelliFireApiMode.LOCAL
    else:
        raise ConfigEntryNotReady("Neither local nor cloud connectivity available")

    # Determine actual control mode with fallback
    if preferred_control == API_MODE_LOCAL:
        if local_available:
            control_mode = IntelliFireApiMode.LOCAL
        elif cloud_available:
            LOGGER.info("Local control unavailable, falling back to cloud")
            control_mode = IntelliFireApiMode.CLOUD
        else:
            raise ConfigEntryNotReady("Neither local nor cloud connectivity available")
    elif cloud_available:
        control_mode = IntelliFireApiMode.CLOUD
    elif local_available:
        LOGGER.info("Cloud control unavailable, falling back to local")
        control_mode = IntelliFireApiMode.LOCAL
    else:
        raise ConfigEntryNotReady("Neither local nor cloud connectivity available")

    # Apply the modes if different from what was set during construction
    if read_mode != fireplace.read_mode:
        await fireplace.set_read_mode(read_mode)
    if control_mode != fireplace.control_mode:
        await fireplace.set_control_mode(control_mode)


async def async_update_options(
    hass: HomeAssistant, entry: IntellifireConfigEntry
) -> None:
    """Handle options update by reloading the config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_wait_for_initialization(
    fireplace: UnifiedFireplace, timeout=STARTUP_TIMEOUT
):
    """Wait for a fireplace to be initialized."""
    while (
        fireplace.data.ipv4_address == "127.0.0.1" and fireplace.data.serial == "unset"
    ):
        LOGGER.debug("Waiting for fireplace to initialize [%s]", fireplace.read_mode)
        await asyncio.sleep(INIT_WAIT_TIME_SECONDS)


async def async_unload_entry(
    hass: HomeAssistant, entry: IntellifireConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
