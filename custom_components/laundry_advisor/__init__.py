"""Laundry Advisor integration for Home Assistant."""

from __future__ import annotations

from typing import TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import LaundryAdvisorCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

LaundryAdvisorConfigEntry: TypeAlias = ConfigEntry[LaundryAdvisorCoordinator]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LaundryAdvisorConfigEntry,
) -> bool:
    """Set up Laundry Advisor from a config entry."""
    coordinator = LaundryAdvisorCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: LaundryAdvisorConfigEntry,
) -> bool:
    """Unload a Laundry Advisor config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
