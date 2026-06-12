"""Constants for the Laundry Advisor integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "laundry_advisor"

CONF_WEATHER_ENTITY: Final = "weather_entity"
CONF_FORECAST_HOURS: Final = "forecast_hours"
CONF_UPDATE_INTERVAL: Final = "update_interval"

DEFAULT_FORECAST_HOURS: Final = 12
DEFAULT_UPDATE_INTERVAL_MINUTES: Final = 30
DEFAULT_UPDATE_INTERVAL: Final = timedelta(minutes=DEFAULT_UPDATE_INTERVAL_MINUTES)

MIN_FORECAST_HOURS: Final = 3
MAX_FORECAST_HOURS: Final = 48
MIN_UPDATE_INTERVAL_MINUTES: Final = 5
MAX_UPDATE_INTERVAL_MINUTES: Final = 240

ATTR_INDEX: Final = "laundry_index"
ATTR_STATUS: Final = "laundry_status"
ATTR_RECOMMENDATION: Final = "laundry_recommendation"
ATTR_DRYING_WINDOW: Final = "drying_window"
ATTR_WEATHER_ENTITY: Final = "weather_entity"
ATTR_FORECAST_HOURS: Final = "forecast_hours"

STATUS_EXCELLENT: Final = "Excellent"
STATUS_GOOD: Final = "Good"
STATUS_FAIR: Final = "Fair"
STATUS_POOR: Final = "Poor"

DRYING_WINDOW_NONE: Final = "No suitable drying window"
