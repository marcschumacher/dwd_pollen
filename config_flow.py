from homeassistant import config_entries
from .const import (
    DOMAIN,
    CONF_PARTREGION_ID,
    CONF_POLLEN_TYPE,
    CONF_DAYS,
)
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from . import get_pollen_data
import logging


class DwdPollenSensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """DWD Pollen config flow."""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL
    _options = None
    _LOGGER = logging.getLogger(__name__)

    def __init__(self):
        """Initialize flow."""

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""

        if user_input is not None:
            return self.async_create_entry(
                title="%d/%s/%s" % (user_input[CONF_PARTREGION_ID] + "/",
                                    user_input[CONF_POLLEN_TYPE] + "/",
                                    user_input[CONF_DAYS]),
                data={
                    "partregion_id": user_input[CONF_PARTREGION_ID],
                    "pollen_type": user_input[CONF_POLLEN_TYPE],
                    "days": user_input[CONF_DAYS],
                }
            )

        pollen_data = await get_pollen_data(self.hass)

        self._LOGGER.debug("DWD DATA: %s" % pollen_data)

        data_schema = {
            vol.Required(CONF_PARTREGION_ID):
                vol.In(await self.get_partregions(pollen_data)),
            vol.Required(CONF_POLLEN_TYPE):
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
                    }),
            vol.Required(CONF_DAYS):
                cv.multi_select(
                    {
                        'today': 'Heute',
                        'tomorrow': 'Morgen',
                        'dayafter_tomorrow': 'Übermorgen',
                    }),
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(data_schema))

    async def get_partregions(self, pollen_data):
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
