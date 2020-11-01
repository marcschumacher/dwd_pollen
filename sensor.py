"""Sensor platform for DWD pollen information."""
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from datetime import timedelta
from datetime import datetime

from .const import (
    CONF_PARTREGION_ID,
    CONF_POLLEN_TYPE,
    CONF_DAYS,
    STAT_MIN,
    STAT_MAX,
    STAT_AVG
)
from . import get_coordinator
import logging

DAY_ADJUSTMENTS = {
    'today': 0,
    'tomorrow': 1,
    'dayafter_tomorrow': 2}

REST_API_KEY_POLLEN = 'Pollen'

REST_API_KEY_PARTREGION_NAME = 'partregion_name'

REST_API_KEY_REGION_NAME = 'region_name'

REST_API_KEY_PARTREGION_ID = 'partregion_id'

REST_API_KEY_CONTENT = 'content'

REST_API_KEY_LAST_UPDATE = "last_update"

SENSORDATA_POLLENDATA = 'pollendata'

SENSORDATA_PARTREGION_NAME = 'partregion_name'

SENSORDATA_REGION_NAME = 'region_name'

ATTRIBUTION = "Data provided by DWD"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Defer sensor setup to the shared sensor module."""
    coordinator = await get_coordinator(hass)

    partregion_ids = config_entry.data[CONF_PARTREGION_ID]
    include_pollen = config_entry.data[CONF_POLLEN_TYPE]
    include_days = config_entry.data[CONF_DAYS]

    sensors = []
    for partregion_id in partregion_ids:
        for day in include_days:
            for polle in include_pollen:
                sensors.append(DwdPollenSensor(coordinator, partregion_id, day, polle))
            sensors.append(DwdPollenStatisticSensor(coordinator, partregion_id, day, STAT_MIN))
            sensors.append(DwdPollenStatisticSensor(coordinator, partregion_id, day, STAT_MAX))
            sensors.append(DwdPollenStatisticSensor(coordinator, partregion_id, day, STAT_AVG))

    async_add_entities(sensors)


def get_today(offset):
    return datetime.today().date() + timedelta(days=offset)


class DwdPollenSensor(CoordinatorEntity):
    """Representation of a DWD pollen sensor."""

    def __init__(self, coordinator, partregion_id, day, internal_pollen_id):
        """Initialize a DWD pollen sensor."""
        super().__init__(coordinator)
        self._partregion_id = partregion_id
        self._internal_pollen_id = internal_pollen_id
        self._day = day

    @property
    def available(self):
        """Return if sensor is available."""
        return self.coordinator.last_update_success

    @property
    def state(self):
        """Return the state of the sensor."""
        this_date = get_today(DAY_ADJUSTMENTS[self._day])
        if this_date in self.coordinator.data.sensordata[self._partregion_id]['data'] and \
                self._internal_pollen_id in \
                self.coordinator.data.sensordata[self._partregion_id]['data'][this_date][
                    SENSORDATA_POLLENDATA]:
            return \
                self.coordinator.data.sensordata[self._partregion_id]['data'][this_date][
                    SENSORDATA_POLLENDATA][
                    self._internal_pollen_id]['value']
        return None

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return "mdi:flower-outline"

    @property
    def device_state_attributes(self):
        """Return the state attributes of the DWD pollen information."""
        this_date = get_today(DAY_ADJUSTMENTS[self._day])
        last_updated = self.coordinator.last_update_success.isoformat()
        region_name = self.coordinator.data.sensordata[self._partregion_id][SENSORDATA_REGION_NAME]
        partregion_name = self.coordinator.data.sensordata[self._partregion_id][SENSORDATA_PARTREGION_NAME]
        if self.state is None:
            original_value = None
            description = None
        else:
            original_value = \
                self.coordinator.data.sensordata[self._partregion_id]['data'][this_date][
                    SENSORDATA_POLLENDATA][
                    self._internal_pollen_id]['id']
            description = \
                self.coordinator.data.sensordata[self._partregion_id]['data'][this_date][
                    SENSORDATA_POLLENDATA][
                    self._internal_pollen_id]['descr']
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            'last_updated': last_updated,
            'region_name': region_name,
            'partregion_name': partregion_name,
            'original_value': original_value,
            'description': description,
        }


class DwdPollenStatisticSensor(CoordinatorEntity):
    """Representation statistics for all DWD pollen sensors."""

    def __init__(self, coordinator, partregion_id, day, statistic_type):
        """Initialize the statistics DWD pollen sensor."""
        super().__init__(coordinator)
        self._partregion_id = partregion_id
        self._statistic_type = statistic_type
        self._day = day

    @property
    def available(self):
        """Return if sensor is available."""
        return self.coordinator.last_update_success

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return "mdi:flower-outline"

    @property
    def state(self):
        """Return the state of the sensor, which is the date of the last update."""
        this_date = get_today(DAY_ADJUSTMENTS[self._day])
        if this_date in self.coordinator.data.sensordata[self._partregion_id]['data'] and \
                self._statistic_type in self.coordinator.data.sensordata[self._partregion_id]['data'][this_date]['stats']:
            return self.coordinator.data.sensordata[self._partregion_id]['data'][this_date]['stats'][self._statistic_type]['value']
        return None

    @property
    def device_state_attributes(self):
        """Return the state attributes of the DWD pollen information."""
        this_date = get_today(DAY_ADJUSTMENTS[self._day])
        if self.state is None:
            description = None
        else:
            description = self.coordinator.data.sensordata[self._partregion_id]['data'][this_date]['stats'][self._statistic_type][
                'descr']
        partregion_name = self.coordinator.data.sensordata[self._partregion_id][SENSORDATA_PARTREGION_NAME]
        region_name = self.coordinator.data.sensordata[self._partregion_id][SENSORDATA_REGION_NAME]
        last_update = self.coordinator.data.last_update
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            'last_updated': last_update,
            'region_name': region_name,
            'partregion_name': partregion_name,
            'description': description,
        }
