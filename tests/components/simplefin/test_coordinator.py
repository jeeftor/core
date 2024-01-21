"""Test the data update coordinator - hopefully in a HA approved manner."""
from unittest.mock import AsyncMock, patch

import pytest
from simplefin4py.exceptions import SimpleFinAuthError, SimpleFinPaymentRequiredError

from homeassistant.components.simplefin.coordinator import (
    SimpleFinDataUpdateCoordinator,
)
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady


@pytest.mark.asyncio
async def test_update_data_success():
    """Test the update data success."""
    sf_client = AsyncMock()
    coordinator = SimpleFinDataUpdateCoordinator(None, sf_client)

    await coordinator._async_update_data()

    sf_client.fetch_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_data_auth_error():
    """Test the auth error."""
    sf_client = AsyncMock()
    sf_client.fetch_data.side_effect = SimpleFinAuthError
    coordinator = SimpleFinDataUpdateCoordinator(None, sf_client)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()

    sf_client.fetch_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_data_payment_required_error():
    """Test the payment required error."""
    sf_client = AsyncMock()
    sf_client.fetch_data.side_effect = SimpleFinPaymentRequiredError
    coordinator = SimpleFinDataUpdateCoordinator(None, sf_client)

    with patch(
        "homeassistant.components.simplefin.coordinator.LOGGER.warning"
    ) as mock_warning, pytest.raises(ConfigEntryNotReady):
        await coordinator._async_update_data()

    sf_client.fetch_data.assert_awaited_once()
    mock_warning.assert_called_once_with(
        "There is a billing info with your SimpleFin Account. Please correct and try again later"
    )
