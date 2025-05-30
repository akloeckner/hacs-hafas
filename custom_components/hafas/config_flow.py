"""Config flow for HaFAS integration."""
from __future__ import annotations

import logging
from typing import Any
from enum import StrEnum

from pyhafas import HafasClient
from pyhafas.profile import KVBProfile, NASAProfile, RKRPProfile, VSNProfile
from pyhafas.types.fptf import Station
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_OFFSET
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_DESTINATION,
    CONF_ONLY_DIRECT,
    CONF_PRODUCTS,
    CONF_PROFILE,
    CONF_START,
    DOMAIN,
)
_LOGGER = logging.getLogger(__name__)


class Profile(StrEnum):
    """Enum of HaFAS profile type."""

    KVB = "KVB"
    NASA = "NASA"
    RKRP = "RKRP"
    VSN = "VSN"


PROFILE_OPTIONS = [
    selector.SelectOptionDict(
        value=Profile.KVB,
        label="Kölner Verkehrs-Betriebe",
    ),
    selector.SelectOptionDict(
        value=Profile.NASA,
        label="Nahverkehr Sachsen-Anhalt"
    ),
    selector.SelectOptionDict(
        value=Profile.RKRP,
        label="Rejseplanen"
    ),
    selector.SelectOptionDict(
        value=Profile.VSN,
        label="Verkehrsverbund Süd-Niedersachsen"
    ),
]

DEFAULT_OFFSET = {"seconds": 0}

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PROFILE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=PROFILE_OPTIONS,
                multiple=False,
                mode=selector.SelectSelectorMode.DROPDOWN,
            ),
        ),
        vol.Required(CONF_START): str,
        vol.Required(CONF_DESTINATION): str,
        vol.Required(CONF_OFFSET, default=DEFAULT_OFFSET): selector.DurationSelector(),
        vol.Required(CONF_ONLY_DIRECT, default=False): bool,
    }
)


def get_user_station_schema(
    start_stations: list[str], destination_stations: list[str]
) -> vol.Schema:
    """Create config schema based on the fetched stations."""

    start_stations_options = [
        selector.SelectOptionDict(value=station, label=station)
        for station in start_stations
    ]

    destination_stations_options = [
        selector.SelectOptionDict(value=station, label=station)
        for station in destination_stations
    ]

    return vol.Schema(
        {
            vol.Required(
                CONF_START, default=start_stations[0]
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=start_stations_options,
                    multiple=False,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                ),
            ),
            vol.Required(
                CONF_DESTINATION, default=destination_stations[0]
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=destination_stations_options,
                    multiple=False,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                ),
            ),
        }
    )


def get_user_product_schema(profile: str) -> vol.Schema:
    """Create config schema for available products in a profile."""
    client: HafasClient = get_client(profile)

    options = [ key for key in client.profile.availableProducts]

    return vol.Schema(
        {
            vol.Required(
                CONF_PRODUCTS, default=client.profile.defaultProducts
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="products",
                )
            ),
        }
    )


def get_client(profile: Profile) -> HafasClient:
    """Create a HafasClient from a Profile choice."""

    if profile == Profile.DB:
        return HafasClient(DBProfile())
    elif profile == Profile.KVB:
        return HafasClient(KVBProfile())
    elif profile == Profile.NASA:
        return HafasClient(NASAProfile())
    elif profile == Profile.RKRP:
        return HafasClient(RKRPProfile())
    elif profile == Profile.VSN:
        return HafasClient(VSNProfile())


def get_stations(client: HafasClient, station_name: str) -> Station:
    """Fetch available stations based on user input."""

    stations = client.locations(station_name)

    return [s.name for s in stations]


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    client: HafasClient = get_client(data[CONF_PROFILE])

    start_stations = await hass.async_add_executor_job(
        get_stations, client, data[CONF_START]
    )
    if len(start_stations) == 0:
        raise ValueError(f'No station found with name "{data[CONF_START]}".')

    destination_stations = await hass.async_add_executor_job(
        get_stations, client, data[CONF_DESTINATION]
    )
    if len(destination_stations) == 0:
        raise ValueError(f'No station found with name "{data[CONF_DESTINATION]}".')

    # Return info that you want to store in the config entry.
    return {
        CONF_PROFILE: data[CONF_PROFILE],
        CONF_START: start_stations,
        CONF_DESTINATION: destination_stations,
        CONF_OFFSET: data[CONF_OFFSET],
        CONF_ONLY_DIRECT: data[CONF_ONLY_DIRECT],
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HaFAS."""

    VERSION = 1
    data: dict[str, Any]


    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            self.data = await validate_input(self.hass, user_input)
        except ValueError as ex:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception: %s", ex)
            errors["base"] = "invalid_station"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return await self.async_step_stations()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


    async def async_step_stations(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the station selection step."""

        if user_input is None:
            schema = get_user_station_schema(
                self.data[CONF_START], self.data[CONF_DESTINATION]
            )
            return self.async_show_form(
                step_id="stations", data_schema=schema
            )

        self.data = self.data | user_input

        return await self.async_step_products()


    async def async_step_products(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the product selection step."""

        if user_input is None:
            schema = get_user_product_schema(
                self.data[CONF_PROFILE]
            )
            return self.async_show_form(
                step_id="products", data_schema=schema
            )

        self.data = self.data | user_input

        title = f"{self.data[CONF_START]} to {self.data[CONF_DESTINATION]}"

        return self.async_create_entry(title=title, data=self.data)
