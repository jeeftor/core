"""Test fixtures for SimpleFIN."""
from unittest.mock import MagicMock, patch

import pytest
from simplefin4py import FinancialData
from simplefin4py.exceptions import SimpleFinInvalidClaimTokenError

from tests.common import load_json_value_fixture


@pytest.fixture
def mock_get_financial_data() -> FinancialData:
    """Fixture to mock the fetch_data method of SimpleFin."""
    fixture_data = load_json_value_fixture("simplefin/fin_data.json")

    fin_data = FinancialData(fixture_data)
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
