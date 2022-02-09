"""Intellifire Climate Entities."""
from __future__ import annotations

from dataclasses import dataclass

from intellifire4py import IntellifirePollData

from homeassistant.components.climate import (
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
    ClimateEntity,
    ClimateEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IntellifireDataUpdateCoordinator
from .const import DOMAIN, LOGGER
from .entity import IntellifireEntity


@dataclass
class IntellifireClimateEntityDescription(ClimateEntityDescription):
    """Describes a fan entity."""


INTELLIFIRE_CLIMATES: tuple[IntellifireClimateEntityDescription, ...] = (
    IntellifireClimateEntityDescription(key="climate", name="Thermostat"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the fans."""
    coordinator: IntellifireDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        IntellifireClimate(
            coordinator=coordinator,
            description=description,
            # entity_registry_enabled_default=bool(coordinator.api.data.has_thermostat)
        )
        for description in INTELLIFIRE_CLIMATES
    )


class IntellifireClimate(IntellifireEntity, ClimateEntity):
    """Intellifire climate entity."""

    entity_description: IntellifireClimateEntityDescription

    # _attr_hvac_mode = HVAC_MODE_OFF
    _attr_hvac_modes = [HVAC_MODE_HEAT, HVAC_MODE_OFF]
    _attr_min_temp = 0
    _attr_max_temp = 37
    _attr_supported_features = SUPPORT_TARGET_TEMPERATURE
    _attr_target_temperature_step = 1.0
    _attr_temperature_unit = TEMP_CELSIUS
    last_temp = 21

    @property
    def hvac_mode(self) -> str:
        """Return current hvac mode."""
        if self.coordinator.api.data.thermostat_on:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    async def async_set_temperature(self, **kwargs) -> None:
        """Turn on thermostat by setting a target temperature."""
        raw_target_temp = kwargs[ATTR_TEMPERATURE]
        self.last_temp = int(raw_target_temp)
        LOGGER.info(
            f"setting target temp to {int(raw_target_temp)}c { (raw_target_temp * 9 / 5) + 32 }f"
        )
        await self.coordinator.control_api.set_thermostat_c(
            fireplace=self.coordinator.control_api.default_fireplace,
            temp_c=self.last_temp,
        )

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return float(self.coordinator.api.data.temperature_c)

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        return float(self.coordinator.api.data.thermostat_setpoint_c)

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set HVAC mode to normal or thermostat control."""
        LOGGER.info(f"Setting mode to[{hvac_mode} - using last temp: {self.last_temp}")

        # Is there a way to use a := here?
        if hvac_mode == HVAC_MODE_HEAT:
            # 1) Make sure the fireplace is on!
            await self.coordinator.control_api.flame_on(
                fireplace=self.coordinator.control_api.default_fireplace,
            )
            # 2) Set the desired target temp
            await self.coordinator.control_api.set_thermostat_c(
                fireplace=self.coordinator.control_api.default_fireplace,
                temp_c=self.last_temp,
            )
        if hvac_mode == HVAC_MODE_OFF:
            # self.last_temp = int(self.target_temperature)
            await self.coordinator.control_api.turn_off_thermostat(
                fireplace=self.coordinator.control_api.default_fireplace
            )
