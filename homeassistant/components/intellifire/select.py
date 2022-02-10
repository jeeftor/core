"""Select entities for intellifire."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from intellifire4py import IntellifireControlAsync, IntellifirePollData

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import IntellifireDataUpdateCoordinator
from .entity import IntellifireEntity


@dataclass
class IntellifireSensorRequiredKeysMixin:
    """Mixin for the Sensors."""

    # default_option: str
    select_fn: Callable[[IntellifireControlAsync, int], Awaitable]
    value_fn: Callable[[IntellifirePollData], str]
    internal_options: list[int]  # What is used internally
    external_options: list[str]  # What is shown on GUI
    select_field_name: str


@dataclass
class IntellifireSelectEntityDescription(
    SelectEntityDescription, IntellifireSensorRequiredKeysMixin
):
    """Placeholder description."""


INTELLIFIRE_SELECTS: tuple[IntellifireSelectEntityDescription, ...] = (
    IntellifireSelectEntityDescription(
        key="flame_height",
        name="Flame Height",
        icon="mdi:arrow-expand-vertical",
        value_fn=lambda data: data.flameheight,
        internal_options=[0, 1, 2, 3, 4],
        external_options=["Super Low", "Low", "Medium", "High", "Super High"],
        select_fn=lambda control_api, height: control_api.set_flame_height(
            fireplace=control_api.default_fireplace, height=height
        ),
        select_field_name="flameheight",
    ),
)


class IntellifireSelect(IntellifireEntity, SelectEntity):
    """Intellifire Select Class."""

    entity_description: IntellifireSelectEntityDescription

    def _get_internal_option(self, *, external_option) -> int:
        """Convert an external option to internal."""
        option_index = self.entity_description.external_options.index(external_option)
        return self.entity_description.internal_options[option_index]

    def _get_external_option(self, *, internal_option: int | str) -> str:
        """Convert an internal option to external."""
        option_index = self.entity_description.internal_options.index(
            int(internal_option)
        )
        return self.entity_description.external_options[option_index]

    @property
    def current_option(self) -> str | None:
        """Get the current option to use."""
        raw_value_str = str(self.entity_description.value_fn(self.coordinator.api.data))
        return self._get_external_option(internal_option=raw_value_str)

    @property
    def options(self) -> list[str]:
        """Use external options for GUI display."""
        return self.entity_description.external_options

    async def async_select_option(self, option: str) -> None:
        """Select the option and send it to the control API."""
        internal_option = self._get_internal_option(external_option=option)
        await self.entity_description.select_fn(
            self.coordinator.control_api, internal_option
        )
        setattr(
            self.coordinator.api,
            self.entity_description.select_field_name,
            internal_option,
        )
        await self.async_update_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Define setup entry call."""
    coordinator: IntellifireDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    print("ASYNC_SETUP")
    async_add_entities(
        IntellifireSelect(coordinator=coordinator, description=description)
        for description in INTELLIFIRE_SELECTS
    )
