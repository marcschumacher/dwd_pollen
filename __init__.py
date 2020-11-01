"""DWD pollen integration."""
import asyncio
import logging

import async_timeout
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import aiohttp_client, entity_registry, update_coordinator

from .const import (
    DOMAIN,
    DWD_POLLEN_URL,
    CONF_PARTREGION_ID
)

PLATFORMS = ["sensor"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the DWD pollen component."""
    # Make sure coordinator is initialized.
    await get_coordinator(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up DWD pollen from a config entry."""
    if isinstance(entry.data[CONF_PARTREGION_ID], int):
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_PARTREGION_ID: entry.title}
        )

    if not entry.unique_id:
        hass.config_entries.async_update_entry(entry, unique_id=entry.data[CONF_PARTREGION_ID])

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    return unload_ok


async def get_coordinator(hass):
    """Get the data update coordinator."""
    if DOMAIN in hass.data:
        return hass.data[DOMAIN]

    async def async_get_pollen_data():
        _LOGGER.debug("Retrieving DWD pollen data")
        with async_timeout.timeout(30):
            session = aiohttp_client.async_get_clientsession(hass)
            resp = await session.get(DWD_POLLEN_URL)
            return await resp.json(content_type=None)

    hass.data[DOMAIN] = update_coordinator.DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        name=DOMAIN,
        update_method=async_get_pollen_data,
        update_interval=timedelta(hours=1),
    )
    await hass.data[DOMAIN].async_refresh()
    return hass.data[DOMAIN]
