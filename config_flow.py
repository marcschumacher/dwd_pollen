from homeassistant import config_entries
from .const import (
    DOMAIN,
    CONF_PARTREGION_ID,
    CONF_POLLEN_TYPE,
    CONF_DAYS,
)
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import logging
from . import get_coordinator


class DwdPollenSensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """DWD Pollen config flow."""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL
    _LOGGER = logging.getLogger(__name__)

    def __init__(self):
        """Initialize flow."""

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""

        coordinator = await get_coordinator(self.hass)

        self._LOGGER.debug("DWD DATA: %s" % coordinator.data)

        partregion_dict = await self.async_get_partregions(coordinator.data)

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_PARTREGION_ID])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=partregion_dict[user_input[CONF_PARTREGION_ID]],
                data=user_input
            )

        data_schema = {
            vol.Required(CONF_PARTREGION_ID):
                vol.In(partregion_dict),
            vol.Required(CONF_POLLEN_TYPE):
                vol.All(
                    cv.multi_select(
                        {
                            'birke': 'Birke',
                            'graeser': 'Gräser',
                            'esche': 'Esche',
                            'erle': 'Erle',
                            'hasel': 'Hasel',
                            'beifuss': 'Beifuss',
                            'ambrosia': 'Ambrosia',
                            'roggen': 'Roggen'
                        })
                ),
            vol.Required(CONF_DAYS):
                cv.multi_select(
                    {
                        'today': 'Heute',
                        'tomorrow': 'Morgen',
                        'dayafter_tomorrow': 'Übermorgen',
                    }),
        }

        return self.async_show_form(step_id="user", data_schema=vol.Schema(data_schema))

    async def async_get_partregions(self, pollen_data):
        result = {}
        for entry in pollen_data['content']:
            partregion_id = entry['partregion_id']
            partregion_name = entry['partregion_name']
            region_name = entry['region_name']
            if partregion_name:
                result[partregion_id] = "%s - %s" % (region_name, partregion_name)
            else:
                result[partregion_id] = region_name
        return result
