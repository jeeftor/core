"""Test config flow."""

from unittest.mock import AsyncMock, patch

import pytest
from simplefin4py import FinancialData
from simplefin4py.exceptions import (
    SimpleFinAuthError,
    SimpleFinClaimError,
    SimpleFinInvalidAccountURLError,
    SimpleFinInvalidClaimTokenError,
    SimpleFinPaymentRequiredError,
)

from homeassistant import config_entries
from homeassistant.components.simplefin import CONF_ACCESS_URL, DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_access_url(hass: HomeAssistant, mock_get_financial_data) -> None:
    """Test standard config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ACCESS_URL: "http://user:password@string"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    "side_effect, error_key",  # noqa: PT006
    [
        (SimpleFinInvalidAccountURLError, "url_error"),
        (SimpleFinPaymentRequiredError, "payment_required"),
        (SimpleFinAuthError, "auth_error"),
    ],
)
async def test_access_url_errors(
    hass: HomeAssistant, mock_get_financial_data, side_effect: Exception, error_key: str
) -> None:
    """Test the various errors we can get in access_url mode."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    with patch(
        "homeassistant.components.simplefin.config_flow.SimpleFin.claim_setup_token",
        side_effect=side_effect,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ACCESS_URL: "donJulio"},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": error_key}

    # Pass the entry creation
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ACCESS_URL: "http://user:password@string"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    "side_effect, error_key",  # noqa: PT006
    [
        (SimpleFinInvalidClaimTokenError, "invalid_claim_token"),
        (SimpleFinClaimError, "claim_error"),
    ],
)
async def test_claim_token_errors(
    hass: HomeAssistant, mock_get_financial_data: FinancialData, side_effect, error_key
) -> None:
    """Test config flow with various token claim errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    with patch(
        "homeassistant.components.simplefin.config_flow.SimpleFin.claim_setup_token",
        side_effect=side_effect,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ACCESS_URL: "donJulio"},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": error_key}

    # Finally succeed in creating the item
    with patch(
        "homeassistant.components.simplefin.config_flow.SimpleFin.claim_setup_token",
        return_value="https://i:am@yomama.house.com",
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ACCESS_URL: "donJulio"},
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_successful_claim(
    hass: HomeAssistant,
    mock_get_financial_data: FinancialData,
) -> None:
    """Test successful token claim in config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    with patch(
        "homeassistant.components.simplefin.config_flow.SimpleFin.claim_setup_token",
        return_value="https://i:am@yomama.house.com",
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ACCESS_URL: "donJulio"},
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_reauth_flow(
    hass: HomeAssistant, mock_setup_entry: AsyncMock, mock_get_financial_data
) -> None:
    """Test reauth flow."""
    MOCK_TOKEN = "http://user:password@string"
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ACCESS_URL: "https://i:am@yomama.house.com"},
        version=1,
        unique_id=MOCK_TOKEN,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": "reauth",
            "unique_id": entry.unique_id,
            "entry_id": entry.entry_id,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    # Mock _validate_and_get_errors to return an error the first time, and a valid URL the second time
    with patch(
        "homeassistant.components.simplefin.config_flow._validate_and_get_errors",
        side_effect=[
            ("test_url", {"base": "url_error"}),  # First call returns an error
        ],
    ):
        # Call async_step_reauth_confirm, this should trigger the error
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ACCESS_URL: MOCK_TOKEN},
        )
        await hass.async_block_till_done()
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "url_error"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ACCESS_URL: MOCK_TOKEN},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"