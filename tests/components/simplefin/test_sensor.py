"""Sensor tests."""


from unittest.mock import AsyncMock, patch

import pytest
from simplefin4py.model import AccountType

from homeassistant.components.simplefin.coordinator import (
    SimpleFinDataUpdateCoordinator,
)
from homeassistant.components.simplefin.sensor import SimpleFinSensor


@pytest.mark.parametrize(
    "account_type, expected_icon",  # noqa: PT006
    [
        (AccountType.CHECKING, "mdi:checkbook"),
        (AccountType.CREDIT_CARD, "mdi:credit-card"),
        (AccountType.SAVINGS, "mdi:piggy-bank-outline"),
        (AccountType.INVESTMENT, "mdi:chart-areaspline"),
        (AccountType.MORTGAGE, "mdi:home-city-outline"),
        ("UNKNOWN", "mdi:cash"),
    ],
)
async def test_simplefin_balance_sensor_icon(account_type, expected_icon):
    """Test the sensor icon for different account types."""
    account = AsyncMock()
    account.id = "test_id"
    account.inferred_account_type = account_type
    with patch(
        "homeassistant.components.simplefin.coordinator.SimpleFin.Account.get_account_for_id",
    ) as mock_fetch_data:
        mock_fetch_data.return_value = account
        yield
        coordinator = SimpleFinDataUpdateCoordinator(None, account)
        sensor = SimpleFinSensor(account, coordinator)
        assert sensor.icon == expected_icon
