"""Button definition for Intellifire."""
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
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
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
class IntellifireButtonRequiredKeysMixin:
    """Mixin for required keys."""

    button_fn: Callable[[IntellifireControlAsync],  None]

@dataclass
class IntellifireButtonEntityDescription(ButtonEntityDescription, IntellifireButtonRequiredKeysMixin):
    """Describe a button entity."""


INTELLIFIRE_BUTTONS: tuple[IntellifireButtonEntityDescription, ...] = (
    IntellifireButtonEntityDescription(
        key="beep",
        name="Annoying Beep",
        button_fn=lambda control_api: control_api.beep(
            fireplace=control_api.default_fireplace
        ),
        icon="mdi:air-horn"
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the fans."""
    coordinator: IntellifireDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        IntellifireButton(
            coordinator=coordinator,
            description=description,
        )
        for description in INTELLIFIRE_BUTTONS
    )

class IntellifireButton(IntellifireEntity, ButtonEntity):
    """This is our button definition!"""

    entity_description: IntellifireButtonEntityDescription

    async def async_press(self) -> None:
        """Fire a press event."""
        await self.entity_description.button_fn(self.coordinator.control_api)