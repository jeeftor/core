"""Define switch func."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from intellifire4py.control import IntelliFireControlMode

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import IntellifireDataUpdateCoordinator
from .entity import IntellifireEntity


@dataclass()
class IntelliFireSwitchRequiredKeysMixin:
    """Mixin for required keys."""

    # on_fn: Callable[[IntelliFireController], Awaitable]
    # off_fn: Callable[[IntelliFireController], Awaitable]
    # value_fn: Callable[[IntelliFirePollData], bool]

    on_fn: Callable[[IntellifireDataUpdateCoordinator], Awaitable]
    off_fn: Callable[[IntellifireDataUpdateCoordinator], Awaitable]
    value_fn: Callable[[IntellifireDataUpdateCoordinator], bool]


@dataclass
class IntelliFireSwitchEntityDescription(
    SwitchEntityDescription, IntelliFireSwitchRequiredKeysMixin
):
    """Describes a switch entity."""


INTELLIFIRE_SWITCHES: tuple[IntelliFireSwitchEntityDescription, ...] = (
    IntelliFireSwitchEntityDescription(
        key="on_off",
        name="Flame",
        on_fn=lambda coordinator: coordinator.control_api.flame_on(),
        off_fn=lambda coordinator: coordinator.control_api.flame_off(),
        value_fn=lambda coordinator: coordinator.read_api.data.is_on,
    ),
    IntelliFireSwitchEntityDescription(
        key="pilot",
        name="Pilot light",
        icon="mdi:fire-alert",
        on_fn=lambda coordinator: coordinator.control_api.pilot_on(),
        off_fn=lambda coordinator: coordinator.control_api.pilot_off(),
        value_fn=lambda coordinator: coordinator.read_api.data.pilot_on,
    ),
    IntelliFireSwitchEntityDescription(
        key="cloud_read",
        name="Cloud read",
        on_fn=lambda coordinator: coordinator.set_read_mode(
            IntelliFireControlMode.CLOUD
        ),
        off_fn=lambda coordinator: coordinator.set_read_mode(
            IntelliFireControlMode.LOCAL
        ),
        value_fn=lambda data: (data.read_mode == IntelliFireControlMode.CLOUD),
    ),
    IntelliFireSwitchEntityDescription(
        key="cloud_control",
        name="Cloud control",
        on_fn=lambda coordinator: coordinator.set_control_mode(
            IntelliFireControlMode.CLOUD
        ),
        off_fn=lambda coordinator: coordinator.set_control_mode(
            IntelliFireControlMode.LOCAL
        ),
        value_fn=lambda data: (data.control_mode == IntelliFireControlMode.CLOUD),
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
        IntelliFireSwitch(coordinator=coordinator, description=description)
        for description in INTELLIFIRE_SWITCHES
    )


class IntelliFireSwitch(IntellifireEntity, SwitchEntity):
    """Define an Intellifire Switch."""

    entity_description: IntelliFireSwitchEntityDescription

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.entity_description.on_fn(self.coordinator)
        await self.async_update_ha_state(force_refresh=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.entity_description.off_fn(self.coordinator)
        await self.async_update_ha_state(force_refresh=True)

    @property
    def is_on(self) -> bool | None:
        """Return the on state."""
        return self.entity_description.value_fn(self.coordinator)

    # @property
    # def icon(self) -> str:
    #     """Return switch icon."""
    #     return "mdi:wifi" if self.is_on else "mdi:wifi-off"
