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
        "load_type": data.load_type,
        "latest_index": data.index,
        "drying_window": data.drying_window,
        "estimated_drying_time": data.estimated_drying_time,
        "status": data.status,
        "tomorrow_index": data.tomorrow_index,
        "breakdown": (
            {
                "rain_score": data.breakdown.rain_score,
                "humidity_score": data.breakdown.humidity_score,
                "temperature_score": data.breakdown.temperature_score,
                "wind_score": data.breakdown.wind_score,
                "solar_score": data.breakdown.solar_score,
                "vpd_kpa": data.breakdown.vpd_kpa,
            }
            if data.breakdown is not None
            else None
        ),
    }
