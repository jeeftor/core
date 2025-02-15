"""The tests for light recorder."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from homeassistant.components import light
from homeassistant.components.light import (
    _DEPRECATED_ATTR_COLOR_TEMP,
    _DEPRECATED_ATTR_MAX_MIREDS,
    _DEPRECATED_ATTR_MIN_MIREDS,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_HS_COLOR,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_RGBWW_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_XY_COLOR,
    DOMAIN,
)
from homeassistant.components.recorder import Recorder
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.const import ATTR_FRIENDLY_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from tests.common import async_fire_time_changed
from tests.components.recorder.common import async_wait_recording_done


@pytest.fixture(autouse=True)
async def light_only() -> None:
    """Enable only the light platform."""
    with patch(
        "homeassistant.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.LIGHT],
    ):
        yield


async def test_exclude_attributes(recorder_mock: Recorder, hass: HomeAssistant) -> None:
    """Test light registered attributes to be excluded."""
    now = dt_util.utcnow()
    assert await async_setup_component(hass, "homeassistant", {})
    await async_setup_component(
        hass, light.DOMAIN, {light.DOMAIN: {"platform": "demo"}}
    )
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5))
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)

    states = await hass.async_add_executor_job(
        get_significant_states, hass, now, None, hass.states.async_entity_ids(DOMAIN)
    )
    assert len(states) >= 1
    for entity_states in states.values():
        for state in entity_states:
            assert _DEPRECATED_ATTR_MIN_MIREDS.value not in state.attributes
            assert _DEPRECATED_ATTR_MAX_MIREDS.value not in state.attributes
            assert ATTR_SUPPORTED_COLOR_MODES not in state.attributes
            assert ATTR_EFFECT_LIST not in state.attributes
            assert ATTR_FRIENDLY_NAME in state.attributes
            assert ATTR_MAX_COLOR_TEMP_KELVIN not in state.attributes
            assert ATTR_MIN_COLOR_TEMP_KELVIN not in state.attributes
            assert ATTR_BRIGHTNESS not in state.attributes
            assert ATTR_COLOR_MODE not in state.attributes
            assert _DEPRECATED_ATTR_COLOR_TEMP.value not in state.attributes
            assert ATTR_COLOR_TEMP_KELVIN not in state.attributes
            assert ATTR_EFFECT not in state.attributes
            assert ATTR_HS_COLOR not in state.attributes
            assert ATTR_RGB_COLOR not in state.attributes
            assert ATTR_RGBW_COLOR not in state.attributes
            assert ATTR_RGBWW_COLOR not in state.attributes
            assert ATTR_XY_COLOR not in state.attributes
