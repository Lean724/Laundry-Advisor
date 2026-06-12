"""Diagnostics support for Laundry Advisor."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import LaundryAdvisorConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: LaundryAdvisorConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data

    return {
        "weather_entity": data.weather_entity,
        "forecast_hours": data.forecast_hours,
        "latest_index": data.index,
        "drying_window": data.drying_window,
        "status": data.status,
        "tomorrow_index": data.tomorrow_index,
    }
