"""Button definition for Intellifire."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Awaitable

from intellifire4py import IntellifireControlAsync

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.components.intellifire import IntellifireDataUpdateCoordinator
from homeassistant.components.intellifire.entity import IntellifireEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER


@dataclass
class IntellifireButtonRequiredKeysMixin:
    """Mixin for required keys."""

    button_fn: Callable[[IntellifireControlAsync], Awaitable]


@dataclass
class IntellifireButtonEntityDescription(
    ButtonEntityDescription, IntellifireButtonRequiredKeysMixin
):
    """Describe a button entity."""


INTELLIFIRE_BUTTONS: tuple[IntellifireButtonEntityDescription, ...] = (
    IntellifireButtonEntityDescription(
        key="height_0",
        name="Flame 0",
        button_fn=lambda control_api: control_api.set_flame_height(
            fireplace=control_api.default_fireplace, height=0
        ),
    ),
    IntellifireButtonEntityDescription(
        key="height_1",
        name="Flame 1",
        button_fn=lambda control_api: control_api.set_flame_height(
            fireplace=control_api.default_fireplace, height=1
        ),
    ),
    IntellifireButtonEntityDescription(
        key="height_2",
        name="Flame 2",
        button_fn=lambda control_api: control_api.set_flame_height(
            fireplace=control_api.default_fireplace, height=2
        ),
    ),
    IntellifireButtonEntityDescription(
        key="height_3",
        name="Flame 3",
        button_fn=lambda control_api: control_api.set_flame_height(
            fireplace=control_api.default_fireplace, height=3
        ),
    ),
    IntellifireButtonEntityDescription(
        key="height_4",
        name="Flame 4",
        button_fn=lambda control_api: control_api.set_flame_height(
            fireplace=control_api.default_fireplace, height=4
        ),
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
    """This is our button definition."""

    entity_description: IntellifireButtonEntityDescription

    async def async_press(self) -> None:
        """Fire a press event."""
        await self.entity_description.button_fn(self.coordinator.control_api)
