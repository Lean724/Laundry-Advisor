"""Constants for the Laundry Advisor integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "laundry_advisor"

CONF_WEATHER_ENTITY: Final = "weather_entity"
CONF_FORECAST_HOURS: Final = "forecast_hours"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_LOAD_TYPE: Final = "load_type"
CONF_TEMP_SENSOR: Final = "temperature_sensor"
CONF_HUMIDITY_SENSOR: Final = "humidity_sensor"
CONF_WIND_SENSOR: Final = "wind_speed_sensor"

LOAD_TYPE_LIGHT: Final = "light"
LOAD_TYPE_STANDARD: Final = "standard"
LOAD_TYPE_HEAVY: Final = "heavy"
LOAD_TYPES: Final[tuple[str, ...]] = (
    LOAD_TYPE_LIGHT,
    LOAD_TYPE_STANDARD,
    LOAD_TYPE_HEAVY,
)
DEFAULT_LOAD_TYPE: Final = LOAD_TYPE_STANDARD

LOAD_TYPE_MULTIPLIERS: Final[dict[str, float]] = {
    LOAD_TYPE_LIGHT: 0.70,
    LOAD_TYPE_STANDARD: 1.00,
    LOAD_TYPE_HEAVY: 1.45,
}

DEFAULT_FORECAST_HOURS: Final = 12
DEFAULT_UPDATE_INTERVAL_MINUTES: Final = 30
DEFAULT_UPDATE_INTERVAL: Final = timedelta(minutes=DEFAULT_UPDATE_INTERVAL_MINUTES)
DEFAULT_LANGUAGE: Final = "en"

SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = (
    "en",
    "es",
    "it",
    "pt",
    "ru",
    "de",
    "fr",
    "zh-Hans",
)

MIN_FORECAST_HOURS: Final = 3
MAX_FORECAST_HOURS: Final = 48
MIN_UPDATE_INTERVAL_MINUTES: Final = 5
MAX_UPDATE_INTERVAL_MINUTES: Final = 240

ATTR_INDEX: Final = "laundry_index"
ATTR_STATUS: Final = "laundry_status"
ATTR_RECOMMENDATION: Final = "laundry_recommendation"
ATTR_DRYING_WINDOW: Final = "drying_window"
ATTR_ESTIMATED_DRYING_TIME: Final = "estimated_drying_time"
ATTR_WEATHER_ENTITY: Final = "weather_entity"
ATTR_FORECAST_HOURS: Final = "forecast_hours"
ATTR_LOAD_TYPE: Final = "load_type"
ATTR_RAIN_SCORE: Final = "rain_score"
ATTR_HUMIDITY_SCORE: Final = "humidity_score"
ATTR_TEMPERATURE_SCORE: Final = "temperature_score"
ATTR_WIND_SCORE: Final = "wind_score"
ATTR_SOLAR_SCORE: Final = "solar_score"
ATTR_VPD_KPA: Final = "vpd_kpa"
ATTR_TOMORROW_INDEX: Final = "tomorrow_index"
ATTR_HOURLY_SCORES: Final = "hourly_scores"

STATUS_EXCELLENT: Final = "Excellent"
STATUS_GOOD: Final = "Good"
STATUS_FAIR: Final = "Fair"
STATUS_POOR: Final = "Poor"

DRYING_WINDOW_NONE: Final = "No suitable drying window"
