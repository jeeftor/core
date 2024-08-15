"""Test intelliFire Sensors."""

from unittest.mock import patch

from freezegun import freeze_time
import pytest
from syrupy import SnapshotAssertion

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


@freeze_time("2021-01-01T12:00:00Z")
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_all_sensor_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    mock_config_entry_current: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    mock_fp,
) -> None:
    """Test all entities."""
    with (
        patch("homeassistant.components.intellifire.PLATFORMS", [Platform.SWITCH]),
        patch(
            "intellifire4py.unified_fireplace.UnifiedFireplace.build_fireplace_from_common",
            return_value=mock_fp,
        ),
    ):
        await setup_integration(hass, mock_config_entry_current)

        await snapshot_platform(
            hass, entity_registry, snapshot, mock_config_entry_current.entry_id
        )


async def test_switch(
    hass: HomeAssistant,
    mock_config_entry_current: MockConfigEntry,
    mock_fp,
) -> None:
    """Test if (config) switches get created."""
    with (
        patch("homeassistant.components.intellifire.PLATFORMS", [Platform.SWITCH]),
        patch(
            "intellifire4py.unified_fireplace.UnifiedFireplace.build_fireplace_from_common",
            return_value=mock_fp,
        ),
    ):
        await setup_integration(hass, mock_config_entry_current)

        test_entity = hass.states.get("switch.intellifire_flame")
        assert test_entity is not None
        assert test_entity.name == "IntelliFire Flame"
        assert test_entity.state == "on"
        assert test_entity.attributes == {
            "attribution": "Data provided by unpublished Intellifire API",
            "friendly_name": "IntelliFire Flame",
        }

        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": test_entity.entity_id},
            blocking=True,
        )

        assert test_entity.state == "off"
