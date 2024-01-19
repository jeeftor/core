"""Platform for sensor integration."""
from __future__ import annotations

from typing import Any

from simplefin4py import Account
from simplefin4py.model import AccountType

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SimpleFinDataUpdateCoordinator


def _enum_to_icon(inferred_type: AccountType) -> str:
    """Based on the inferred account type - guess a starting icon."""
    if inferred_type == AccountType.CHECKING:
        return "mdi:checkbook"
    if inferred_type == AccountType.CREDIT_CARD:
        return "mdi:credit-card"
    if inferred_type == AccountType.SAVINGS:
        return "mdi:piggy-bank-outline"
    if inferred_type == AccountType.INVESTMENT:
        return "mdi:chart-areaspline"
    if inferred_type == AccountType.MORTGAGE:
        return "mdi:home-city-outline"

    return "mdi:cash"


class SimpleFinBalanceSensor(
    CoordinatorEntity[SimpleFinDataUpdateCoordinator], SensorEntity
):
    """Representation of a SimpleFinBalanceSensor."""

    _attr_state_class = SensorStateClass.TOTAL
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_has_entity_name = True

    def __init__(
        self,
        account,
        coordinator: SimpleFinDataUpdateCoordinator,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.account_id = account.id
        self._attr_unique_id = f"account_{account.id}".lower()
        self._attr_name = account.name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account.org.domain)},
            name=account.org.name,
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="SimpleFIN",
            model="Account",
        )

    @property
    def available(self) -> bool:
        """Determine if sensor is available."""
        return True

    @property
    def native_value(self) -> int | None:
        """Return the account balance."""
        return self.coordinator.data.get_account_for_id(self.account_id).balance

    @property
    def icon(self) -> str | None:
        """Utilize the inferred account type value as an icon."""
        return _enum_to_icon(
            self.coordinator.data.get_account_for_id(
                self.account_id
            ).inferred_account_type
        )

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the currency of this account."""
        return self.coordinator.data.get_account_for_id(self.account_id).currency

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional sensor state attributes."""
        account_info: Account = self.coordinator.data.get_account_for_id(
            self.account_id
        )

        # Example attributes
        return {
            "currency": account_info.currency,
            "available_balance": account_info.available_balance,
            "last_update": account_info.last_update,
            # Add more attributes here
        }


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SimpleFIN sensors for config entries."""
    simplefin_coordinator: SimpleFinDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]
    accounts = simplefin_coordinator.data.accounts

    async_add_entities(
        [
            SimpleFinBalanceSensor(account, simplefin_coordinator)
            for account in accounts
        ],
        True,
    )
