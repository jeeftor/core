"""Switch definition."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Awaitable

from intellifire4py import IntellifireControlAsync, IntellifirePollData

from homeassistant.components.intellifire import IntellifireDataUpdateCoordinator
from homeassistant.components.intellifire.entity import IntellifireEntity
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER


@dataclass()
class IntellifireSwitchRequiredKeysMixin:
    """Mixin for required keys."""

    on_fn: Callable[[IntellifireControlAsync], Awaitable]
    off_fn: Callable[[IntellifireControlAsync], Awaitable]
    value_fn: Callable[[IntellifirePollData], bool]
    data_field: str


@dataclass
class IntellifireSwitchEntityDescription(
    SwitchEntityDescription, IntellifireSwitchRequiredKeysMixin
):
    """Describes a switch entity."""


INTELLIFIRE_SWITCHES: tuple[IntellifireSwitchEntityDescription, ...] = (
    IntellifireSwitchEntityDescription(
        key="on_off",
        name="Flame",
        on_fn=lambda control_api: control_api.flame_on(
            fireplace=control_api.default_fireplace
        ),
        off_fn=lambda control_api: control_api.flame_off(
            fireplace=control_api.default_fireplace
        ),
        value_fn=lambda data: data.is_on,
        data_field="is_on",
    ),
    IntellifireSwitchEntityDescription(
        key="pilot",
        name="Pilot Light",
        icon="mdi:fire-alert",
        on_fn=lambda control_api: control_api.pilot_on(
            fireplace=control_api.default_fireplace
        ),
        off_fn=lambda control_api: control_api.pilot_off(
            fireplace=control_api.default_fireplace
        ),
        value_fn=lambda data: data.pilot_on,
        data_field="pilot_on",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configure switch entities."""
    coordinator: IntellifireDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        IntellifireSwitch(coordinator=coordinator, description=description)
        for description in INTELLIFIRE_SWITCHES
    )


class IntellifireSwitch(IntellifireEntity, SwitchEntity):
    """Define an Intellifire Switch."""

    entity_description: IntellifireSwitchEntityDescription

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.entity_description.on_fn(self.coordinator.control_api)
        setattr(self.coordinator.api.data, self.entity_description.data_field, 1)
        await self.async_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.entity_description.off_fn(self.coordinator.control_api)
        setattr(self.coordinator.api.data, self.entity_description.data_field, 0)
        await self.async_update_ha_state()

    @property
    def is_on(self) -> bool | None:
        """Return the on state."""
        return self.entity_description.value_fn(self.coordinator.api.data)

    async def async_update(self) -> None:
        """Tell coordinator to update."""
        await self.coordinator.api.poll()
