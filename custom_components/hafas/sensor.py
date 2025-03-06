"""Sensor for HaFAS."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import functools
from typing import Any

from pyhafas import HafasClient
from pyhafas.types.fptf import Journey, Station

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_OFFSET
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from .const import CONF_DESTINATION, CONF_ONLY_DIRECT, CONF_PROFILE, CONF_START, DOMAIN
from .utils import to_dict

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:timetable"
SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up HaFAS sensor entities based on a config entry."""
    client: HafasClient = hass.data[DOMAIN][entry.entry_id]

    # Already verified to have at least one entry in config_flow.py
    start_station = (
        await hass.async_add_executor_job(client.locations, entry.data[CONF_START])
    )[0]
    destination_station = (
        await hass.async_add_executor_job(
            client.locations, entry.data[CONF_DESTINATION]
        )
    )[0]

    offset = timedelta(**entry.data[CONF_OFFSET])

    async_add_entities(
        [
            HaFAS(
                hass,
                client,
                start_station,
                destination_station,
                offset,
                entry.data[CONF_ONLY_DIRECT],
                entry.title,
                entry.entry_id,
                entry.data[CONF_PROFILE],
            )
        ],
        True,
    )


class HaFAS(SensorEntity):
    """Implementation of a HaFAS sensor."""

    _unrecorded_attributes = frozenset(
        {
            "connections",
        }
    )

    def __init__(
        self,
        hass: HomeAssistant,
        client: HafasClient,
        start_station: Station,
        destination_station: Station,
        offset: timedelta,
        only_direct: bool,
        title: str,
        entry_id: str,
        profile: str,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.client = client
        self.origin = start_station
        self.destination = destination_station
        self.offset = offset
        self.only_direct = only_direct

        self._attr_name = title
        self._attr_icon = ICON
        self._attr_unique_id = entry_id
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_attribution = "Provided by " + profile + " through HaFAS API"
        self._attr_available = False

        self.journeys: list[Journey] = []

    async def async_update(self) -> None:
        """Update the journeys using pyhafas."""

        self._attr_native_value = None
        self._attr_extra_state_attributes = {
            "connections": [],
        }

        try:
            self.journeys = await self.hass.async_add_executor_job(
                functools.partial(
                    self.client.journeys,
                    origin=self.origin,
                    destination=self.destination,
                    date=dt_util.as_local(dt_util.utcnow() + self.offset),
                    max_changes=0 if self.only_direct else -1,
                    max_journeys=3,
                )
            )
        except Exception as e:
            if self.available:
                _LOGGER.warning(f"Couldn't fetch journeys for {self.entity_id}: {e}")
            self._attr_available = False
            return

        self._attr_available = True

        if not self.journeys:
            return

        connections = to_dict(self.journeys)
        self._attr_extra_state_attributes["connections"] = connections

        # use get method, because an empty Journey would return {}
        running = [x for x in connections if not x.get("canceled", True)]

        if not running:
            return

        self._attr_native_value = running[0]["departure"] + (
            dt_util.parse_duration(running[0]["delay"]) or timedelta()
        )

        # use decomposition to not modify the original object
        self._attr_extra_state_attributes = {
            k: v for k, v in running[0].items() if k != "legs"
        } | self._attr_extra_state_attributes
