"""DWD pollen integration."""
import logging

import async_timeout
from homeassistant.helpers import aiohttp_client

from .const import (
    DWD_POLLEN_URL
)

_LOGGER = logging.getLogger(__name__)


async def get_pollen_data(hass):
    """Get DWD pollen data."""
    _LOGGER.debug("Retrieving DWD pollen data")
    with async_timeout.timeout(10):
        session = aiohttp_client.async_get_clientsession(hass)
        resp = await session.get(DWD_POLLEN_URL)
        data = await resp.json(content_type=None)

    return data
