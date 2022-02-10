"""Fan definition for Intellifire."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Awaitable, Callable, Optional, List

from intellifire4py import IntellifireControlAsync, IntellifirePollData

from homeassistant.components.fan import (
    SUPPORT_PRESET_MODE,
    SUPPORT_SET_SPEED,
    FanEntity,
    FanEntityDescription,
)
from .coordinator import IntellifireDataUpdateCoordinator
from .entity import IntellifireEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import DOMAIN, LOGGER


@dataclass
class IntellifireFanRequiredKeysMixin:
    set_fn: Callable[
        [IntellifireControlAsync, int], Awaitable
    ]  # What type actually gets returned... is it a Future?

    value_fn: Callable[[IntellifirePollData], bool]
    data_field: str
    named_speeds: List[str]


@dataclass
class IntellifireFanEntityDescription(
    FanEntityDescription, IntellifireFanRequiredKeysMixin
):
    """Describes a fan entity."""


INTELLIFIRE_FANS: tuple[IntellifireFanEntityDescription, ...] = (
    IntellifireFanEntityDescription(
        key="fan",
        name="Fan",
        set_fn=lambda control_api, speed: control_api.set_fan_speed(
            fireplace=control_api.default_fireplace, speed=speed
        ),
        value_fn=lambda data: data.fanspeed,
        data_field="fanspeed",
        named_speeds=[
            "quiet",
            "low",
            "medium",
            "high",
        ],  # off is not included  # off is not included
    ),
    IntellifireFanEntityDescription(
        key="flame",
        name="Flame Height",
        set_fn=lambda control_api, height: control_api.set_flame_height(
            fireplace=control_api.default_fireplace, height=height
        ),
        icon="mdi:campfire",
        value_fn=lambda data: data.flameheight,
        data_field="flameheight",
        named_speeds=["0", "1", "2", "3", "4"],  # off is not included
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


# NAMED_FAN_SPEEDS = ["quiet", "low", "medium", "high"]  # off is not included


class IntellifireFan(IntellifireEntity, FanEntity):
    """This is Fan entity for the fireplace."""

    entity_description: IntellifireFanEntityDescription

    @property
    def is_on(self):
        """Return on or off."""
        return self.entity_description.value_fn(self.coordinator.api.data) >= 1

    @property
    def percentage(self) -> int | None:
        """Return fan percentage."""
        percent_step = ordered_list_item_to_percentage(
            self.entity_description.named_speeds,
            self.entity_description.named_speeds[0],
        )
        return (
            self.entity_description.value_fn(self.coordinator.api.data) * percent_step
        )

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_SET_SPEED | SUPPORT_PRESET_MODE

    @property
    def speed_count(self) -> int:
        """Count of supported speeds."""
        return len(self.entity_description.named_speeds)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        # Get a percent from the preset

        percent = ordered_list_item_to_percentage(
            self.entity_description.named_speeds, preset_mode
        )
        await self.async_set_percentage(percent)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        # Calculate percentage steps
        percent_step = 100.0 / len(self.entity_description.named_speeds)
        int_value = int(math.ceil(float(percentage) / percent_step))
        await self.entity_description.set_fn(self.coordinator.control_api, int_value)
        setattr(self.coordinator.api, self.entity_description.data_field, int_value)
        await self.async_update_ha_state()
        LOGGER.info(
            f"Fan speed {int_value} [{int_value * 25}%] = {self.entity_description.name}: [{percentage_to_ordered_list_item(self.entity_description.named_speeds, int(int_value * percent_step))}] "
        )

    async def async_turn_on(
        self,
        speed: Optional[str] = None,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        await self.entity_description.set_fn(self.coordinator.control_api, 1)
        setattr(self.coordinator.api, self.entity_description.data_field, 1)
        await self.async_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self.entity_description.set_fn(self.coordinator.control_api, 0)
        setattr(self.coordinator.api, self.entity_description.data_field, 0)
        await self.async_update_ha_state()

        # await self.coordinator.control_api.fan_off(
        #     fireplace=self.coordinator.control_api.default_fireplace
        # )
        # Update HA while we wait for poll to actually re-pull the state info
        # self.coordinator.api.data.fanspeed = 0
        # await self.async_update_ha_state()
