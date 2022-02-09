"""Fan definition for Intellifire."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Optional

from homeassistant.components.fan import (
    SUPPORT_PRESET_MODE,
    SUPPORT_SET_SPEED,
    FanEntity,
    FanEntityDescription,
)
from homeassistant.components.intellifire import IntellifireDataUpdateCoordinator
from homeassistant.components.intellifire.entity import IntellifireEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import DOMAIN, LOGGER


@dataclass
class IntellifireFanEntityDescription(FanEntityDescription):
    """Describes a fan entity."""


INTELLIFIRE_FANS: tuple[IntellifireFanEntityDescription, ...] = (
    IntellifireFanEntityDescription(
        key="fan",
        name="Fan",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the fans."""
    coordinator: IntellifireDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    if coordinator.api.data.has_fan:
        async_add_entities(
            IntellifireFan(coordinator=coordinator, description=description)
            for description in INTELLIFIRE_FANS
        )


NAMED_FAN_SPEEDS = ["quiet", "low", "medium", "high"]  # off is not included


class IntellifireFan(IntellifireEntity, FanEntity):
    """This is Fan entity for the fireplace."""

    entity_description: IntellifireFanEntityDescription

    @property
    def is_on(self):
        """Return on or off."""
        return self.coordinator.api.data.fanspeed >= 1

    @property
    def percentage(self) -> int | None:
        """Return fan percentage."""
        return self.coordinator.api.data.fanspeed * 25

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_SET_SPEED | SUPPORT_PRESET_MODE

    @property
    def speed_count(self) -> int:
        """Count of supported speeds."""
        return 4  # Off and 4 speeds - don't count off?

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        # Get a percent from the preset
        percent = ordered_list_item_to_percentage(NAMED_FAN_SPEEDS, preset_mode)
        await self.async_set_percentage(percent)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        # Fan only supports speed values of 0 (off) 1,2,3,4
        # 0 = 0, 1-25 = 1, 26-50 = 2, 51-75 = 3, 75+ = 4
        int_value = int(math.ceil(float(percentage) / 25))
        await self.coordinator.control_api.set_fan_speed(
            fireplace=self.coordinator.control_api.default_fireplace, speed=int_value
        )
        # Update HA while we wait for the data to be re-polled
        self.coordinator.api.data.fanspeed = int_value
        await self.async_update_ha_state()
        LOGGER.info(
            f"Fan speed {int_value} [{int_value * 25}%] = FAN_MODE: [{percentage_to_ordered_list_item(NAMED_FAN_SPEEDS, int_value * 25)}] "
        )

    async def async_turn_on(
        self,
        speed: Optional[str] = None,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        await self.coordinator.control_api.set_fan_speed(
            fireplace=self.coordinator.control_api.default_fireplace, speed=1
        )
        # Update HA while we wait for poll to actually re-pull the state info
        self.coordinator.api.data.fanspeed = 1
        await self.async_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self.coordinator.control_api.fan_off(
            fireplace=self.coordinator.control_api.default_fireplace
        )
        # Update HA while we wait for poll to actually re-pull the state info
        self.coordinator.api.data.fanspeed = 0
        await self.async_update_ha_state()
