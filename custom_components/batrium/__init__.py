"""
Batrium BMS Home Assistant Integration.

Listens on UDP port 18542 for WatchMon broadcast packets and
exposes battery system data as HA sensors and binary sensors.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

from .const import CONF_UDP_PORT, DEFAULT_UDP_PORT, DOMAIN
from .coordinator import BatriumCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Batrium from a config entry."""
    port = entry.data.get(CONF_UDP_PORT, DEFAULT_UDP_PORT)
    coordinator = BatriumCoordinator(hass, port=port)

    try:
        await coordinator.async_start()
    except OSError:
        _LOGGER.exception("Cannot start Batrium UDP listener")
        return False

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: BatriumCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_stop()
    return unload_ok
