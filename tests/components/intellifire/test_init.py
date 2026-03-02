"""Test the IntelliFire config flow."""

from unittest.mock import AsyncMock, patch

from homeassistant.components.intellifire import CONF_USER_ID
from homeassistant.components.intellifire.const import (
    API_MODE_CLOUD,
    API_MODE_LOCAL,
    CONF_AUTH_COOKIE,
    CONF_CONTROL_MODE,
    CONF_READ_MODE,
    CONF_SERIAL,
    CONF_WEB_CLIENT_ID,
    DOMAIN,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_IP_ADDRESS,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_minor_migration(
    hass: HomeAssistant, mock_config_entry_old, mock_apis_single_fp
) -> None:
    """With the new library we are going to end up rewriting the config entries."""
    mock_config_entry_old.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry_old.entry_id)

    assert mock_config_entry_old.data == {
        "ip_address": "192.168.2.108",
        "host": "192.168.2.108",
        "api_key": "B5C4DA27AAEF31D1FB21AFF9BFA6BCD2",
        "serial": "3FB284769E4736F30C8973A7ED358123",
        "auth_cookie": "B984F21A6378560019F8A1CDE41B6782",
        "web_client_id": "FA2B1C3045601234D0AE17D72F8E975",
        "user_id": "52C3F9E8B9D3AC99F8E4D12345678901FE9A2BC7D85F7654E28BF98BCD123456",
        "username": "grumpypanda@china.cn",
        "password": "you-stole-my-pandas",
    }


async def test_minor_migration_error(hass: HomeAssistant, mock_apis_single_fp) -> None:
    """Test the case where we completely fail to initialize."""
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=1,
        title="Fireplace of testing",
        data={
            CONF_HOST: "11.168.2.218",
            CONF_USERNAME: "grumpypanda@china.cn",
            CONF_PASSWORD: "you-stole-my-pandas",
            CONF_USER_ID: "52C3F9E8B9D3AC99F8E4D12345678901FE9A2BC7D85F7654E28BF98BCD123456",
        },
    )

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.MIGRATION_ERROR


async def test_init_with_no_username(hass: HomeAssistant, mock_apis_single_fp) -> None:
    """Test the case where we completely fail to initialize."""
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=2,
        data={
            CONF_IP_ADDRESS: "192.168.2.108",
            CONF_PASSWORD: "you-stole-my-pandas",
            CONF_SERIAL: "3FB284769E4736F30C8973A7ED358123",
            CONF_WEB_CLIENT_ID: "FA2B1C3045601234D0AE17D72F8E975",
            CONF_API_KEY: "B5C4DA27AAEF31D1FB21AFF9BFA6BCD2",
            CONF_AUTH_COOKIE: "B984F21A6378560019F8A1CDE41B6782",
            CONF_USER_ID: "52C3F9E8B9D3AC99F8E4D12345678901FE9A2BC7D85F7654E28BF98BCD123456",
        },
        options={CONF_READ_MODE: API_MODE_LOCAL, CONF_CONTROL_MODE: API_MODE_CLOUD},
        unique_id="3FB284769E4736F30C8973A7ED358123",
    )

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_connectivity_bad(
    hass: HomeAssistant,
    mock_config_entry_current,
    mock_apis_single_fp,
) -> None:
    """Test a timeout error on the setup flow."""

    with patch(
        "homeassistant.components.intellifire.UnifiedFireplace.build_fireplace_from_common",
        new_callable=AsyncMock,
        side_effect=TimeoutError,
    ):
        mock_config_entry_current.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry_current.entry_id)

        await hass.async_block_till_done()
        assert len(hass.states.async_all()) == 0


async def test_update_options_reloads_entry(
    hass: HomeAssistant,
    mock_config_entry_current: MockConfigEntry,
    mock_apis_single_fp,
) -> None:
    """Test that changing options triggers a config entry reload."""
    _mock_local, _mock_cloud, mock_fp = mock_apis_single_fp

    # Enable both connectivity for this test
    mock_fp.local_connectivity = True
    mock_fp.cloud_connectivity = True

    mock_config_entry_current.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry_current.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry_current.state is ConfigEntryState.LOADED

    # Change options - should trigger reload
    hass.config_entries.async_update_entry(
        mock_config_entry_current,
        options={CONF_READ_MODE: API_MODE_CLOUD, CONF_CONTROL_MODE: API_MODE_CLOUD},
    )
    await hass.async_block_till_done()

    # Entry should still be loaded after reload
    assert mock_config_entry_current.state is ConfigEntryState.LOADED


async def test_setup_fallback_local_to_cloud_read(
    hass: HomeAssistant,
    mock_config_entry_current: MockConfigEntry,
    mock_apis_single_fp,
) -> None:
    """Test that setup falls back to cloud when local read is unavailable."""
    _mock_local, _mock_cloud, mock_fp = mock_apis_single_fp

    # Local unavailable, cloud available
    mock_fp.local_connectivity = False
    mock_fp.cloud_connectivity = True

    mock_config_entry_current.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry_current.entry_id)
    await hass.async_block_till_done()

    # Should have fallen back to cloud for both read and control
    assert mock_config_entry_current.state is ConfigEntryState.LOADED
    mock_fp.set_read_mode.assert_called()
    mock_fp.set_control_mode.assert_called()


async def test_setup_fallback_cloud_to_local_read(
    hass: HomeAssistant,
    mock_apis_single_fp,
) -> None:
    """Test that setup falls back to local when cloud read is unavailable."""
    _mock_local, _mock_cloud, mock_fp = mock_apis_single_fp

    # Cloud unavailable, local available
    mock_fp.local_connectivity = True
    mock_fp.cloud_connectivity = False

    # Create entry with cloud preference
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=2,
        data={
            CONF_IP_ADDRESS: "192.168.2.108",
            CONF_USERNAME: "grumpypanda@china.cn",
            CONF_PASSWORD: "you-stole-my-pandas",
            CONF_SERIAL: "3FB284769E4736F30C8973A7ED358123",
            CONF_WEB_CLIENT_ID: "FA2B1C3045601234D0AE17D72F8E975",
            CONF_API_KEY: "B5C4DA27AAEF31D1FB21AFF9BFA6BCD2",
            CONF_AUTH_COOKIE: "B984F21A6378560019F8A1CDE41B6782",
            CONF_USER_ID: "52C3F9E8B9D3AC99F8E4D12345678901FE9A2BC7D85F7654E28BF98BCD123456",
        },
        options={CONF_READ_MODE: API_MODE_CLOUD, CONF_CONTROL_MODE: API_MODE_CLOUD},
        unique_id="3FB284769E4736F30C8973A7ED358123",
    )

    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Should have fallen back to local - entry should be loaded
    assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_setup_no_connectivity_fails(
    hass: HomeAssistant,
    mock_config_entry_current: MockConfigEntry,
    mock_apis_single_fp,
) -> None:
    """Test that setup fails when neither local nor cloud is available."""
    _mock_local, _mock_cloud, mock_fp = mock_apis_single_fp

    # Neither available
    mock_fp.local_connectivity = False
    mock_fp.cloud_connectivity = False

    mock_config_entry_current.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry_current.entry_id)
    await hass.async_block_till_done()

    # Should fail with retry
    assert mock_config_entry_current.state is ConfigEntryState.SETUP_RETRY
