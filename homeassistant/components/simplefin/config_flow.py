"""Config flow for SimpleFIN integration."""

from typing import Any

from simplefin4py import SimpleFin
from simplefin4py.exceptions import (
    SimpleFinAuthError,
    SimpleFinClaimError,
    SimpleFinInvalidAccountURLError,
    SimpleFinInvalidClaimTokenError,
    SimpleFinPaymentRequiredError,
)
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_TOKEN
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


async def _validate_or_obtain_access_url(input_string: str) -> str:
    """Validate the input string as an access URL or a claim token and fetch data using SimpleFin.

    Args:
        input_string (str): The input_string will either be a URL or a base64 encoded claim_token

    Returns:
        str: The validated access URL - (or throws an error)

    Raises:
        SimpleFinInvalidAccountURLError: If the input string is an invalid access URL.
        SimpleFinPaymentRequiredError
        SimpleFinAuthError
        SimpleFinInvalidClaimTokenError: If the input string is an invalid claim token.
        SimpleFinClaimError: If there's an error in claim token processing.
    """

    # Any exceptions will be handled outside of this function
    access_url = (
        input_string
        if input_string.startswith("http")
        else await SimpleFin.claim_setup_token(input_string)
    )

    # Decode and fetch data for the access URL
    if input_string.startswith("http"):
        SimpleFin.decode_access_url(access_url)
    simple_fin = SimpleFin(access_url=access_url)
    await simple_fin.fetch_data()
    return access_url


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the initial setup of a SimpleFIN integration."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Prompt user for SimpleFIN API credentials."""
        errors = {}

        if user_input is not None:
            try:
                user_input[CONF_API_TOKEN] = await _validate_or_obtain_access_url(
                    user_input[CONF_API_TOKEN]
                )
            except SimpleFinInvalidAccountURLError:
                errors["base"] = "url_error"
            except SimpleFinInvalidClaimTokenError:
                errors["base"] = "invalid_claim_token"
            except SimpleFinClaimError:
                errors["base"] = "claim_error"
            except SimpleFinPaymentRequiredError:
                errors["base"] = "payment_required"
            except SimpleFinAuthError:
                errors["base"] = "auth_error"
            if not errors:
                return self.async_create_entry(
                    title="SimpleFIN", data={"access_url": user_input[CONF_API_TOKEN]}
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_TOKEN): str,
                }
            ),
            errors=errors,
        )
