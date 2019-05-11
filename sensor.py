"""
Support for getting pollen data from the German Deutscher Wetterdienst (DWD)

For configuration of the partregion_id refer to https://opendata.dwd.de/climate_environment/health/alerts/Beschreibung_pollen_s31fg.pdf ("Zuordnungen der region_id, bzw. partregion_id")
"""
import logging
import json
from datetime import timedelta
from datetime import datetime

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION, CONF_NAME)
from homeassistant.util import Throttle
from homeassistant.components.rest.sensor import RestData

STAT_AVG = 'avg'

STAT_MAX = 'max'

STAT_MIN = 'min'

REST_API_KEY_POLLEN = 'Pollen'

REST_API_KEY_PARTREGION_NAME = 'partregion_name'

REST_API_KEY_REGION_NAME = 'region_name'

REST_API_KEY_PARTREGION_ID = 'partregion_id'

REST_API_KEY_CONTENT = 'content'

REST_API_KEY_LAST_UPDATE = "last_update"

SENSORDATA_POLLENDATA = 'pollendata'

SENSORDATA_PARTREGION_NAME = 'partregion_name'

SENSORDATA_REGION_NAME = 'region_name'

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by DWD"

DEFAULT_NAME = 'dwd_pollen'
DEFAULT_INCLUDE_POLLEN = ['birke', 'graeser', 'esche', 'erle', 'hasel', 'beifuss', 'ambrosia', 'roggen']
DEFAULT_INCLUDE_DAYS = ['today', 'tomorrow', 'dayafter_tomorrow']

CONF_PARTREGION_IDS = 'partregion_ids'
CONF_INCLUDE_POLLEN = 'include_pollen'
CONF_INCLUDE_DAYS = 'include_days'

SCAN_INTERVAL = timedelta(minutes=15)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_PARTREGION_IDS): cv.ensure_list,
    vol.Optional(CONF_INCLUDE_POLLEN, default=DEFAULT_INCLUDE_POLLEN): cv.ensure_list,
    vol.Optional(CONF_INCLUDE_DAYS, default=DEFAULT_INCLUDE_DAYS): cv.ensure_list,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

API_TO_HOMEASSISTANT_MAP = {'-1': None, '0': 0, '0-1': 1, '1': 2, '1-2': 3, '2': 4, '2-3': 5, '3': 6}
HOMEASSISTANT_TO_API_MAP = {v: k for k, v in API_TO_HOMEASSISTANT_MAP.items()}

DAY_ADJUSTMENTS = {
    'today': 0,
    'tomorrow': 1,
    'dayafter_tomorrow': 2}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the DWD pollen sensor."""
    entity_name = config.get(CONF_NAME)
    partregion_ids = config.get(CONF_PARTREGION_IDS)
    include_pollen = config.get(CONF_INCLUDE_POLLEN)
    include_days = config.get(CONF_INCLUDE_DAYS)

    api = DwdPollenAPI(partregion_ids)

    sensors = []
    for partregion_id in partregion_ids:
        for day in include_days:
            for polle in include_pollen:
                sensors.append(DwdPollenSensor(api, entity_name, partregion_id, day, polle))
            sensors.append(DwdPollenStatisticSensor(api, entity_name, partregion_id, day, STAT_MIN))
            sensors.append(DwdPollenStatisticSensor(api, entity_name, partregion_id, day, STAT_MAX))
            sensors.append(DwdPollenStatisticSensor(api, entity_name, partregion_id, day, STAT_AVG))

    add_entities(sensors, True)


class DwdPollenAPI:
    """
    Get the latest data and update the states.

    Format of map sensordata:
    sensordata[<region_id>]['region_name']
    sensordata[<region_id>]['partregion_name']
    sensordata[<region_id>]['pollendata'][<pollen_name>]['today'|'today_mapped'|'tomorrow'|'tomorrow_mapped'|'dayafter_tomorrow'|'dayafter_tomorrow_mapped']
    """

    def __init__(self, partregion_ids):
        """Initialize the data object."""
        resource = "https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json"

        self._rest = RestData('GET', resource, None, None, None, True)
        self._partregion_ids = partregion_ids
        self.last_update = None
        self.sensordata = {}
        self.api_id_to_descr = {}
        self.available = False
        self.update()

    @Throttle(SCAN_INTERVAL)
    def update(self):
        """Get the latest pollen_name data from DWD open data site."""
        try:
            # Update DWD weather data by calling rest service
            self._rest.update()
            # Retrieve REST data from correspionding object
            rest_api_result = json.loads(self._rest.data)

            self.last_update = datetime.strptime(rest_api_result[REST_API_KEY_LAST_UPDATE], '%Y-%m-%d %H:%M Uhr')

            self.generate_api_id_to_descr_map(rest_api_result)

            # Iterate over all supplied partregions
            for partregion_data in rest_api_result[REST_API_KEY_CONTENT]:

                current_partregion_id = partregion_data[REST_API_KEY_PARTREGION_ID]

                # Is the current partregion_id included in the ones we should parse?
                if current_partregion_id in self._partregion_ids:
                    self.sensordata[current_partregion_id] = {}
                    self.sensordata[current_partregion_id][SENSORDATA_REGION_NAME] = partregion_data[
                        REST_API_KEY_REGION_NAME]
                    self.sensordata[current_partregion_id][SENSORDATA_PARTREGION_NAME] = partregion_data[
                        REST_API_KEY_PARTREGION_NAME]

                    self.sensordata[current_partregion_id]['data'] = {}
                    self.calculateit(current_partregion_id, partregion_data[REST_API_KEY_POLLEN], 'today',
                                     self.last_update.date())
                    self.calculateit(current_partregion_id, partregion_data[REST_API_KEY_POLLEN], 'tomorrow',
                                     self.last_update.date() + timedelta(days=1))
                    self.calculateit(current_partregion_id, partregion_data[REST_API_KEY_POLLEN], 'dayafter_to',
                                     self.last_update.date() + timedelta(days=2))

            self.available = True
        except TypeError:
            _LOGGER.error("Unable to fetch pollen_name data from DWD opendata server")
            self.available = False

    def calculateit(self, current_partregion_id, pollendata, day, pollen_date):
        """
        Format:
            {
                "41": {
                    "region_name": "<region name>",
                    "partregion_name": "<partregion name>",
                    "data": {
                        "<pollen_date1>": {
                            "pollendata": {
                                "<polle1>": {
                                    "id": "<api ID>",
                                    "descr": "<api description of api ID>",
                                    "value": "<sensor value>"
                                },
                                "<polle2>": {
                                    "id": "<api ID>",
                                    "descr": "<api description of api ID>",
                                    "value": "<sensor value>"
                                }
                                [...]
                            },
                            "stats": {
                                "min": <minimum value>,
                                "max": <maximum value>,
                                "avg": <average value>
                            }
                        },
                        [...]
                    }
                }
            }
        """
        minimum = None
        # minimum = 6
        maximum = None
        # maximum = 0
        total_count = None
        # total_count = 0
        total_sum = None
        # total_sum = 0

        self.sensordata[current_partregion_id]['data'][pollen_date] = {}
        self.sensordata[current_partregion_id]['data'][pollen_date][SENSORDATA_POLLENDATA] = {}

        for pollen_name in pollendata:
            retrieved_pollendata = pollendata[pollen_name]
            internal_pollen_id = str(pollen_name).lower()
            self.sensordata[current_partregion_id]['data'][pollen_date][SENSORDATA_POLLENDATA][internal_pollen_id] = {}

            pollen_amount_api_id = retrieved_pollendata[day]
            pollen_amount_descr = self.api_id_to_descr[pollen_amount_api_id]
            pollen_amount_value = API_TO_HOMEASSISTANT_MAP[pollen_amount_api_id]

            self.sensordata[current_partregion_id]['data'][pollen_date][SENSORDATA_POLLENDATA][internal_pollen_id][
                'id'] = pollen_amount_api_id
            self.sensordata[current_partregion_id]['data'][pollen_date][SENSORDATA_POLLENDATA][internal_pollen_id][
                'descr'] = pollen_amount_descr
            self.sensordata[current_partregion_id]['data'][pollen_date][SENSORDATA_POLLENDATA][internal_pollen_id][
                'value'] = pollen_amount_value

            if pollen_amount_value is not None:
                minimum = pollen_amount_value if minimum is None else min(minimum, pollen_amount_value)
                maximum = pollen_amount_value if maximum is None else max(maximum, pollen_amount_value)
                total_count = 1 if total_count is None else total_count + 1
                total_sum = pollen_amount_value if total_sum is None else total_sum + pollen_amount_value

            _LOGGER.debug("Successfully retrieved pollen_name data for %s (ID %d).",
                          self.sensordata[current_partregion_id][SENSORDATA_PARTREGION_NAME],
                          current_partregion_id)

        self.sensordata[current_partregion_id]['data'][pollen_date]['stats'] = {}
        self.sensordata[current_partregion_id]['data'][pollen_date]['stats'][STAT_MIN] = {}
        self.sensordata[current_partregion_id]['data'][pollen_date]['stats'][STAT_MIN]['value'] = minimum
        minimum_api_id = HOMEASSISTANT_TO_API_MAP[minimum]
        self.sensordata[current_partregion_id]['data'][pollen_date]['stats'][STAT_MIN]['descr'] = self.api_id_to_descr[minimum_api_id]

        self.sensordata[current_partregion_id]['data'][pollen_date]['stats'][STAT_MAX] = {}
        self.sensordata[current_partregion_id]['data'][pollen_date]['stats'][STAT_MAX]['value'] = maximum
        maximum_api_id = HOMEASSISTANT_TO_API_MAP[maximum]
        self.sensordata[current_partregion_id]['data'][pollen_date]['stats'][STAT_MAX]['descr'] = self.api_id_to_descr[maximum_api_id]

        if total_count is None or total_sum is None or total_count <= 0:
            average = None
        else:
            average = total_sum / total_count
        self.sensordata[current_partregion_id]['data'][pollen_date]['stats'][STAT_AVG] = {}
        self.sensordata[current_partregion_id]['data'][pollen_date]['stats'][STAT_AVG]['value'] = average
        average_api_id = None if average is None else HOMEASSISTANT_TO_API_MAP[round(average, 0)]
        self.sensordata[current_partregion_id]['data'][pollen_date]['stats'][STAT_AVG]['descr'] = None if average_api_id is None else self.api_id_to_descr[average_api_id]

    def generate_api_id_to_descr_map(self, json_obj):
        legend_map = json_obj['legend']
        for key, value in legend_map.items():
            if not key.endswith('_desc'):
                self.api_id_to_descr[value] = legend_map["%s_desc" % key]

        self.api_id_to_descr['-1'] = 'n/a'

    def get_adjusted_day(self, day):
        today = datetime.now().date()
        last_update_day = self.last_update.date()
        offset = (today - last_update_day).days
        return DAY_ADJUSTMENTS[day][offset]

    def get_descr_for_value(self, value):
        if not value:
            return None
        api_id = HOMEASSISTANT_TO_API_MAP[value]
        if api_id in self.api_id_to_descr:
            return self.api_id_to_descr[api_id]
        else:
            return None


def get_today(offset):
    return datetime.today().date() + timedelta(days=offset)


class DwdPollenSensor(Entity):
    """Representation of a DWD pollen sensor."""

    def __init__(self, api, entity_name, partregion_id, day, internal_pollen_id):
        """Initialize a DWD pollen sensor."""
        self._api = api
        self._entity_name = entity_name
        self._partregion_id = partregion_id
        self._internal_pollen_id = internal_pollen_id
        self._day = day

    @property
    def name(self):
        """Return the name of the sensor."""
        return "%s_%02d_%s_%s" % (self._entity_name, self._partregion_id, self._day, self._internal_pollen_id)

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return "mdi:flower-outline"

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return ''

    @property
    def state(self):
        """Return the state of the sensor."""
        this_date = get_today(DAY_ADJUSTMENTS[self._day])
        if this_date in self._api.sensordata[self._partregion_id]['data'] and \
                self._internal_pollen_id in self._api.sensordata[self._partregion_id]['data'][this_date][SENSORDATA_POLLENDATA]:
            return self._api.sensordata[self._partregion_id]['data'][this_date][SENSORDATA_POLLENDATA][self._internal_pollen_id]['value']
        return None

    @property
    def device_state_attributes(self):
        """Return the state attributes of the DWD pollen information."""
        this_date = get_today(DAY_ADJUSTMENTS[self._day])
        last_updated = self._api.last_update.isoformat()
        region_name = self._api.sensordata[self._partregion_id][SENSORDATA_REGION_NAME]
        partregion_name = self._api.sensordata[self._partregion_id][SENSORDATA_PARTREGION_NAME]
        if self.state is None:
            original_value = None
            description = None
        else:
            original_value = self._api.sensordata[self._partregion_id]['data'][this_date][SENSORDATA_POLLENDATA][self._internal_pollen_id]['id']
            description = self._api.sensordata[self._partregion_id]['data'][this_date][SENSORDATA_POLLENDATA][self._internal_pollen_id]['descr']
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            'last_updated': last_updated,
            'region_name': region_name,
            'partregion_name': partregion_name,
            'original_value': original_value,
            'description': description,
        }

    @property
    def available(self):
        """Could the device be accessed during the last update call."""
        return self._api.available

    def update(self):
        """Get the latest data from the DWD-Weather-Warnings API."""
        self._api.update()


class DwdPollenStatisticSensor(Entity):
    """Representation statistics for all DWD pollen sensors."""

    def __init__(self, api, entity_name, partregion_id, day, statistic_type):
        """Initialize the statistics DWD pollen sensor."""
        self._api = api
        self._entity_name = entity_name
        self._partregion_id = partregion_id
        self._statistic_type = statistic_type
        self._day = day

    @property
    def name(self):
        """Return the name of the sensor."""
        return "%s_%02d_%s_%s" % (self._entity_name, self._partregion_id, self._day, self._statistic_type)

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return "mdi:flower-outline"

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return ''

    @property
    def state(self):
        """Return the state of the sensor, which is the date of the last update."""
        this_date = get_today(DAY_ADJUSTMENTS[self._day])
        if this_date in self._api.sensordata[self._partregion_id]['data'] and \
                self._statistic_type in self._api.sensordata[self._partregion_id]['data'][this_date]['stats']:
            return self._api.sensordata[self._partregion_id]['data'][this_date]['stats'][self._statistic_type]['value']
        return None

    @property
    def device_state_attributes(self):
        """Return the state attributes of the DWD pollen information."""
        this_date = get_today(DAY_ADJUSTMENTS[self._day])
        if self.state is None:
            description = None
        else:
            description = self._api.sensordata[self._partregion_id]['data'][this_date]['stats'][self._statistic_type]['descr']
        partregion_name = self._api.sensordata[self._partregion_id][SENSORDATA_PARTREGION_NAME]
        region_name = self._api.sensordata[self._partregion_id][SENSORDATA_REGION_NAME]
        last_update = self._api.last_update
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            'last_updated': last_update,
            'region_name': region_name,
            'partregion_name': partregion_name,
            'description': description,
        }

    @property
    def available(self):
        """Could the device be accessed during the last update call."""
        return self._api.available

    def update(self):
        """Get the latest data from the DWD-Weather-Warnings API."""
        self._api.update()
