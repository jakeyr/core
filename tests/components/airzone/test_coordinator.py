"""Define tests for the Airzone coordinator."""

from unittest.mock import patch

from aioairzone.exceptions import (
    AirzoneError,
    HotWaterNotAvailable,
    InvalidMethod,
    SystemOutOfRange,
)
from freezegun.api import FrozenDateTimeFactory

from homeassistant.components.airzone.const import DOMAIN
from homeassistant.components.airzone.coordinator import SCAN_INTERVAL
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.util.dt import utcnow

from .util import CONFIG, HVAC_MOCK, HVAC_MOCK_NEW_ZONES, HVAC_VERSION_MOCK

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_coordinator_client_connector_error(hass: HomeAssistant) -> None:
    """Test ClientConnectorError on coordinator update."""

    config_entry = MockConfigEntry(
        minor_version=2,
        data=CONFIG,
        domain=DOMAIN,
        unique_id="airzone_unique_id",
    )
    config_entry.add_to_hass(hass)

    with (
        patch(
            "homeassistant.components.airzone.AirzoneLocalApi.get_dhw",
            side_effect=HotWaterNotAvailable,
        ),
        patch(
            "homeassistant.components.airzone.AirzoneLocalApi.get_hvac",
            return_value=HVAC_MOCK,
        ) as mock_hvac,
        patch(
            "homeassistant.components.airzone.AirzoneLocalApi.get_hvac_systems",
            side_effect=SystemOutOfRange,
        ),
        patch(
            "homeassistant.components.airzone.AirzoneLocalApi.get_version",
            return_value=HVAC_VERSION_MOCK,
        ),
        patch(
            "homeassistant.components.airzone.AirzoneLocalApi.get_webserver",
            side_effect=InvalidMethod,
        ),
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        mock_hvac.assert_called_once()
        mock_hvac.reset_mock()

        mock_hvac.side_effect = AirzoneError
        async_fire_time_changed(hass, utcnow() + SCAN_INTERVAL)
        await hass.async_block_till_done()
        mock_hvac.assert_called_once()

        state = hass.states.get("sensor.despacho_temperature")
        assert state.state == STATE_UNAVAILABLE


async def test_coordinator_new_devices(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test new devices on coordinator update."""

    config_entry = MockConfigEntry(
        minor_version=2,
        data=CONFIG,
        domain=DOMAIN,
        unique_id="airzone_unique_id",
    )
    config_entry.add_to_hass(hass)

    with (
        patch(
            "homeassistant.components.airzone.AirzoneLocalApi.get_dhw",
            side_effect=HotWaterNotAvailable,
        ),
        patch(
            "homeassistant.components.airzone.AirzoneLocalApi.get_hvac",
            return_value=HVAC_MOCK_NEW_ZONES,
        ) as mock_hvac,
        patch(
            "homeassistant.components.airzone.AirzoneLocalApi.get_hvac_systems",
            side_effect=SystemOutOfRange,
        ),
        patch(
            "homeassistant.components.airzone.AirzoneLocalApi.get_version",
            return_value=HVAC_VERSION_MOCK,
        ),
        patch(
            "homeassistant.components.airzone.AirzoneLocalApi.get_webserver",
            side_effect=InvalidMethod,
        ),
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        mock_hvac.assert_called_once()
        mock_hvac.reset_mock()

        state = hass.states.get("sensor.salon_temperature")
        assert state.state == "19.6"

        state = hass.states.get("sensor.dorm_ppal_temperature")
        assert state is None

        mock_hvac.return_value = HVAC_MOCK
        freezer.tick(SCAN_INTERVAL)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        mock_hvac.assert_called_once()

        state = hass.states.get("sensor.salon_temperature")
        assert state.state == "19.6"

        state = hass.states.get("sensor.dorm_ppal_temperature")
        assert state.state == "21.1"
