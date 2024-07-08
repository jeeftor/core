"""Test fixtures for SimpleFIN."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from simplefin4py import FinancialData
from simplefin4py.exceptions import SimpleFinInvalidClaimTokenError

from homeassistant.components.simplefin import CONF_ACCESS_URL
from homeassistant.components.simplefin.const import DOMAIN

from tests.common import MockConfigEntry, load_fixture


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Mock setting up a config entry."""
    with patch(
        "homeassistant.components.simplefin.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_access_url() -> str:
    """Fixture to mock the access_url method of SimpleFin."""
    return "https://i:am@yomama.house.com"


@pytest.fixture
async def mock_config_entry(mock_access_url: str) -> MockConfigEntry:
    """Fixture for MockConfigEntry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ACCESS_URL: mock_access_url},
        version=1,
    )


@pytest.fixture
def mock_get_financial_data() -> FinancialData:
    """Fixture to mock the fetch_data method of SimpleFin."""
    fixture_data = load_fixture("fin_data.json", DOMAIN)

    fin_data = FinancialData.from_json(fixture_data)
    with patch(
        "homeassistant.components.simplefin.coordinator.SimpleFin.fetch_data",
    ) as mock_fetch_data:
        mock_fetch_data.return_value = fin_data
        yield


@pytest.fixture
def mock_claim_setup_token() -> str:
    """Fixture to mock the claim_setup_token method of SimpleFin."""
    with patch(
        "homeassistant.components.simplefin.config_flow.SimpleFin.claim_setup_token",
    ) as mock_claim_setup_token:
        mock_claim_setup_token.return_value = "https://i:am@yomama.comma"
        yield


@pytest.fixture
def mock_decode_claim_token_invalid_then_good() -> str:
    """Fixture to mock the decode_claim_token method of SimpleFin."""
    return_values = [SimpleFinInvalidClaimTokenError, "valid_return_value"]
    with patch(
        "homeassistant.components.simplefin.config_flow.SimpleFin.decode_claim_token",
        new_callable=lambda: MagicMock(side_effect=return_values),
    ):
        yield


@pytest.fixture
def mock_simplefin_client(mock_access_url: str) -> Generator[AsyncMock]:
    """Mock a SimpleFin client."""

    with (
        patch(
            "homeassistant.components.simplefin.SimpleFin",
            autospec=True,
        ) as mock_client,
        patch(
            "simplefin4py.SimpleFin",
            new=mock_client,
        ),
    ):
        client = mock_client.return_value

        fixture_data = load_fixture("fin_data.json", DOMAIN)
        fin_data = FinancialData.from_json(fixture_data)

        assert fin_data.accounts != []
        client.fetch_data.return_value = fin_data

        client.access_url = mock_access_url

        yield client
