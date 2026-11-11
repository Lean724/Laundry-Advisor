"""Coordinator and calculation engine for Laundry Advisor."""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any, Protocol, cast

from homeassistant.components.weather import Forecast
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import SpeedConverter, TemperatureConverter

from .const import (
    CONF_FORECAST_HOURS,
    CONF_HUMIDITY_SENSOR,
    CONF_LOAD_TYPE,
    CONF_TEMP_SENSOR,
    CONF_UPDATE_INTERVAL,
    CONF_WEATHER_ENTITY,
    CONF_WIND_SENSOR,
    DEFAULT_FORECAST_HOURS,
    DEFAULT_LANGUAGE,
    DEFAULT_LOAD_TYPE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    LOAD_TYPE_MULTIPLIERS,
)
from .localization import (
    ALL_STATUS_EXCELLENT,
    ALL_STATUS_FAIR,
    ALL_STATUS_GOOD,
    get_localized_strings,
    is_no_drying_window,
)

_LOGGER = logging.getLogger(__name__)

HOURLY_FORECAST_TYPE = "hourly"
DAILY_FORECAST_TYPE = "daily"
SIGNIFICANTLY_BETTER_DELTA = 15.0
BASE_IDEAL_DRYING_HOURS = 3.0


class LaundryContextProvider(Protocol):
    """Future extension point for energy-aware laundry decisions."""

    async def async_get_adjustment(self) -> float:
        """Return a future score adjustment in points."""


@dataclass(frozen=True, slots=True)
class LaundryForecastPoint:
    """Normalized forecast data used by the scoring engine."""

    datetime: datetime
    temperature: float | None
    humidity: float | None
    precipitation_probability: float | None
    wind_speed: float | None
    condition: str | None
    dew_point: float | None = None
    uv_index: float | None = None
    cloud_coverage: float | None = None
    is_daytime: bool | None = None


@dataclass(frozen=True, slots=True)
class LaundryScoreBreakdown:
    """Detailed component breakdown and hourly curve for dashboard cards."""

    rain_score: int
    humidity_score: int
    temperature_score: int
    wind_score: int
    solar_score: int
    vpd_kpa: float
    hourly_scores: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class LaundryAdvisorData:
    """Calculated data exposed by Laundry Advisor entities."""

    index: int
    status: str
    recommendation: str
    drying_window: str
    good_day: bool
    weather_entity: str
    forecast_hours: int
    forecast: tuple[LaundryForecastPoint, ...]
    tomorrow_index: int | None = None
    estimated_drying_time: float | None = None
    load_type: str = DEFAULT_LOAD_TYPE
    breakdown: LaundryScoreBreakdown | None = None


class LaundryAdvisorCoordinator(DataUpdateCoordinator[LaundryAdvisorData]):
    """Fetch weather forecasts and calculate laundry advice."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.config_entry = config_entry
        update_interval_minutes = int(
            config_entry.options.get(
                CONF_UPDATE_INTERVAL,
                config_entry.data.get(CONF_UPDATE_INTERVAL),
            )
            or DEFAULT_UPDATE_INTERVAL.total_seconds() // 60
        )

        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval_minutes),
            config_entry=config_entry,
        )

    @property
    def weather_entity(self) -> str:
        """Return the configured weather entity."""
        return cast(
            str,
            self.config_entry.options.get(
                CONF_WEATHER_ENTITY,
                self.config_entry.data[CONF_WEATHER_ENTITY],
            ),
        )

    @property
    def forecast_hours(self) -> int:
        """Return the configured forecast horizon."""
        return int(
            self.config_entry.options.get(
                CONF_FORECAST_HOURS,
                self.config_entry.data.get(CONF_FORECAST_HOURS, DEFAULT_FORECAST_HOURS),
            )
        )

    @property
    def load_type(self) -> str:
        """Return the configured laundry load type."""
        return str(
            self.config_entry.options.get(
                CONF_LOAD_TYPE,
                self.config_entry.data.get(CONF_LOAD_TYPE, DEFAULT_LOAD_TYPE),
            )
        )

    def _get_option_or_data(self, key: str) -> str | None:
        """Return an optional entity ID from config entry options or data."""
        if key in self.config_entry.options:
            val = self.config_entry.options.get(key)
            return str(val) if val else None
        val = self.config_entry.data.get(key)
        return str(val) if val else None

    def _read_numeric_sensor(
        self,
        entity_id: str | None,
        target_unit: str | None = None,
    ) -> float | None:
        """Read a float state from an optional local sensor entity."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", ""):
            return None
        value = _as_float(state.state)
        unit = (
            state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            if state.attributes
            else None
        )
        if (
            value is None
            or target_unit is None
            or not isinstance(unit, str)
            or not unit
        ):
            return value
        if target_unit == UnitOfTemperature.CELSIUS:
            return _convert_temperature(value, unit)
        if target_unit == UnitOfSpeed.KILOMETERS_PER_HOUR:
            return _convert_wind_speed(value, unit)
        return value

    async def _async_update_data(self) -> LaundryAdvisorData:
        """Fetch the latest forecast and calculate laundry advice."""
        forecast: list[LaundryForecastPoint] = []
        try:
            forecast = await self._async_get_hourly_forecast()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug(
                "Hourly forecast unavailable for %s: %s",
                self.weather_entity,
                err,
            )

        if not forecast:
            try:
                forecast = await self._async_get_daily_forecast_as_points()
            except Exception as err:
                msg = f"Unable to fetch weather forecast: {err}"
                raise UpdateFailed(msg) from err

        if not forecast:
            raise UpdateFailed("Weather entity did not return forecast data")

        forecast = apply_local_overrides(
            forecast,
            temperature=self._read_numeric_sensor(
                self._get_option_or_data(CONF_TEMP_SENSOR),
                UnitOfTemperature.CELSIUS,
            ),
            humidity=self._read_numeric_sensor(
                self._get_option_or_data(CONF_HUMIDITY_SENSOR)
            ),
            wind_speed=self._read_numeric_sensor(
                self._get_option_or_data(CONF_WIND_SENSOR),
                UnitOfSpeed.KILOMETERS_PER_HOUR,
            ),
        )

        horizon = self.forecast_hours
        primary_forecast = tuple(forecast[:horizon])
        tomorrow_forecast = _tomorrow_forecast(forecast)
        language = getattr(self.hass.config, "language", DEFAULT_LANGUAGE)
        current_load_type = self.load_type

        index = calculate_laundry_index(primary_forecast)
        tomorrow_index = (
            calculate_laundry_index(tomorrow_forecast) if tomorrow_forecast else None
        )
        drying_window = calculate_drying_window(primary_forecast, language=language)
        status = status_from_index(index, language=language)
        recommendation = build_recommendation(
            index=index,
            status=status,
            forecast=primary_forecast,
            drying_window=drying_window,
            tomorrow_index=tomorrow_index,
            language=language,
        )
        estimated_drying_time = calculate_estimated_drying_time(
            primary_forecast,
            load_type=current_load_type,
        )
        breakdown = calculate_score_breakdown(primary_forecast)

        return LaundryAdvisorData(
            index=index,
            status=status,
            recommendation=recommendation,
            drying_window=drying_window,
            good_day=index >= 60 and not is_no_drying_window(drying_window),
            weather_entity=self.weather_entity,
            forecast_hours=horizon,
            forecast=primary_forecast,
            tomorrow_index=tomorrow_index,
            estimated_drying_time=estimated_drying_time,
            load_type=current_load_type,
            breakdown=breakdown,
        )

    async def _async_get_forecast_points(
        self,
        forecast_type: str,
    ) -> list[LaundryForecastPoint]:
        """Fetch forecast data from weather entity using Home Assistant action."""
        response = await self.hass.services.async_call(
            domain="weather",
            service="get_forecasts",
            service_data={
                "entity_id": self.weather_entity,
                "type": forecast_type,
            },
            blocking=True,
            return_response=True,
        )
        forecast_dict = cast(dict[str, Any], response or {})
        raw_forecast = _extract_forecast_list(forecast_dict, self.weather_entity)
        units = getattr(self.hass.config, "units", None)
        temperature_unit = getattr(
            units,
            "temperature_unit",
            UnitOfTemperature.CELSIUS,
        )
        wind_speed_unit = getattr(
            units,
            "wind_speed_unit",
            UnitOfSpeed.KILOMETERS_PER_HOUR,
        )
        return [
            _normalize_forecast_point(
                item,
                temperature_unit=temperature_unit,
                wind_speed_unit=wind_speed_unit,
            )
            for item in raw_forecast
        ]

    async def _async_get_hourly_forecast(self) -> list[LaundryForecastPoint]:
        """Fetch and normalize an hourly forecast using Home Assistant APIs."""
        return await self._async_get_forecast_points(HOURLY_FORECAST_TYPE)

    async def _async_get_daily_forecast_as_points(self) -> list[LaundryForecastPoint]:
        """Fallback for weather entities that only expose daily forecasts."""
        points = await self._async_get_forecast_points(DAILY_FORECAST_TYPE)
        expanded: list[LaundryForecastPoint] = []

        for point in points:
            expanded.extend(
                LaundryForecastPoint(
                    datetime=point.datetime + timedelta(hours=hour),
                    temperature=point.temperature,
                    humidity=point.humidity,
                    precipitation_probability=point.precipitation_probability,
                    wind_speed=point.wind_speed,
                    condition=point.condition,
                    dew_point=point.dew_point,
                    uv_index=point.uv_index,
                    cloud_coverage=point.cloud_coverage,
                    is_daytime=point.is_daytime,
                )
                for hour in range(24)
            )

        return expanded


def apply_local_overrides(
    forecast: Sequence[LaundryForecastPoint],
    *,
    temperature: float | None = None,
    humidity: float | None = None,
    wind_speed: float | None = None,
) -> list[LaundryForecastPoint]:
    """Blend real-time local outdoor sensor readings into the first forecast point."""
    points = list(forecast)
    if not points:
        return points

    first = points[0]
    points[0] = replace(
        first,
        temperature=temperature if temperature is not None else first.temperature,
        humidity=humidity if humidity is not None else first.humidity,
        wind_speed=wind_speed if wind_speed is not None else first.wind_speed,
    )
    return points


def _extract_forecast_list(
    forecasts: dict[str, Any],
    weather_entity: str,
) -> Sequence[Forecast]:
    """Extract the forecast list from Home Assistant's forecast response."""
    entity_forecast = forecasts.get(weather_entity)
    if entity_forecast is None:
        return ()
    forecast = entity_forecast.get("forecast", ())
    return cast(Sequence[Forecast], forecast)


def _convert_temperature(
    value: float | None,
    from_unit: str | None,
) -> float | None:
    """Convert a temperature value to Celsius."""
    if value is None or not from_unit:
        return value
    try:
        return float(
            TemperatureConverter.convert(
                value,
                from_unit,
                UnitOfTemperature.CELSIUS,
            )
        )
    except Exception:  # noqa: BLE001
        return value


def _convert_wind_speed(
    value: float | None,
    from_unit: str | None,
) -> float | None:
    """Convert a wind speed value to km/h."""
    if value is None or not from_unit:
        return value
    try:
        return float(
            SpeedConverter.convert(
                value,
                from_unit,
                UnitOfSpeed.KILOMETERS_PER_HOUR,
            )
        )
    except Exception:  # noqa: BLE001
        return value


def _normalize_forecast_point(
    forecast: Forecast,
    *,
    temperature_unit: str = UnitOfTemperature.CELSIUS,
    wind_speed_unit: str = UnitOfSpeed.KILOMETERS_PER_HOUR,
) -> LaundryForecastPoint:
    """Normalize Home Assistant forecast dictionaries into scoring points."""
    forecast_dict = cast(dict[str, Any], forecast)
    raw_datetime = forecast_dict.get("datetime")
    point_datetime = (
        dt_util.parse_datetime(raw_datetime) if isinstance(raw_datetime, str) else None
    )
    if point_datetime is None:
        point_datetime = dt_util.utcnow()

    raw_temp = forecast_dict.get("native_temperature")
    if raw_temp is None:
        raw_temp = forecast_dict.get("temperature")

    raw_wind = forecast_dict.get("native_wind_speed")
    if raw_wind is None:
        raw_wind = forecast_dict.get("wind_speed")

    raw_dew = forecast_dict.get("native_dew_point")
    if raw_dew is None:
        raw_dew = forecast_dict.get("dew_point")

    raw_daytime = forecast_dict.get("is_daytime")
    is_daytime = bool(raw_daytime) if isinstance(raw_daytime, bool) else None

    return LaundryForecastPoint(
        datetime=dt_util.as_local(point_datetime),
        temperature=_convert_temperature(_as_float(raw_temp), temperature_unit),
        humidity=_as_float(forecast_dict.get("humidity")),
        precipitation_probability=_as_float(
            forecast_dict.get("precipitation_probability")
        ),
        wind_speed=_convert_wind_speed(_as_float(raw_wind), wind_speed_unit),
        condition=(
            str(forecast_dict["condition"]) if forecast_dict.get("condition") else None
        ),
        dew_point=_convert_temperature(_as_float(raw_dew), temperature_unit),
        uv_index=_as_float(forecast_dict.get("uv_index")),
        cloud_coverage=_as_float(forecast_dict.get("cloud_coverage")),
        is_daytime=is_daytime,
    )


def calculate_vpd_kpa(
    temperature: float | None,
    humidity: float | None,
    dew_point: float | None = None,
) -> float:
    """Calculate Vapor Pressure Deficit (kPa) using the Tetens equation."""
    if temperature is None:
        return 0.8

    es = 0.61078 * math.exp((17.27 * temperature) / (temperature + 237.3))
    if dew_point is not None:
        ea = 0.61078 * math.exp((17.27 * dew_point) / (dew_point + 237.3))
    elif humidity is not None:
        clamped_rh = max(0.0, min(humidity, 100.0))
        ea = es * (clamped_rh / 100.0)
    else:
        return 0.8

    return round(max(0.0, es - ea), 2)


def _dew_point_depression(point: LaundryForecastPoint) -> float:
    """Return temperature minus dew point (C) to detect condensation risk."""
    if point.temperature is None:
        return 5.0
    if point.dew_point is not None:
        return point.temperature - point.dew_point
    if point.humidity is not None:
        return max(0.0, (100.0 - min(100.0, point.humidity)) / 5.0)
    return 5.0


def _solar_adjustment(point: LaundryForecastPoint) -> float:
    """Calculate a solar/UV/nighttime adjustment in score points (-12 to +6)."""
    adjustment = 0.0
    if point.is_daytime is False or point.condition == "clear-night":
        adjustment -= 10.0

    if point.uv_index is not None:
        if point.uv_index >= 6.0:
            adjustment += 5.0
        elif point.uv_index >= 3.0:
            adjustment += 2.5
        elif point.uv_index == 0.0 and point.is_daytime is False:
            adjustment -= 2.0

    if point.cloud_coverage is not None and point.cloud_coverage >= 85.0:
        adjustment -= 3.0

    if _dew_point_depression(point) < 2.0:
        adjustment -= 10.0

    return adjustment


def _solar_score(point: LaundryForecastPoint) -> float:
    """Return a 0-100 solar drying score for breakdown metrics."""
    if point.is_daytime is False or point.condition == "clear-night":
        return 20.0
    base = 75.0
    if point.condition == "sunny":
        base = 95.0
    elif point.condition == "partlycloudy":
        base = 80.0
    elif point.condition == "cloudy":
        base = 55.0
    elif _condition_is_rainy(point.condition):
        base = 20.0

    if point.uv_index is not None:
        base = max(base, min(100.0, 40.0 + point.uv_index * 8.0))
    if point.cloud_coverage is not None:
        base = base * (1.0 - (max(0.0, min(point.cloud_coverage, 100.0)) / 250.0))

    return max(0.0, min(100.0, base))


def calculate_point_score(point: LaundryForecastPoint) -> int:
    """Calculate the 0-100 Laundry Index for a single forecast hour."""
    rain = _rain_score(point.precipitation_probability, point.condition)
    humidity = _humidity_score(point.humidity)
    temperature = _temperature_score(point.temperature)
    wind = _wind_score(point.wind_speed)
    base_score = rain * 0.40 + humidity * 0.25 + temperature * 0.20 + wind * 0.15
    adjusted = base_score + _solar_adjustment(point)
    return round(max(0.0, min(adjusted, 100.0)))


def calculate_laundry_index(forecast: Sequence[LaundryForecastPoint]) -> int:
    """Calculate the weighted Laundry Index on a 0-100 scale."""
    if not forecast:
        return 0

    rain = _average(
        _rain_score(point.precipitation_probability, point.condition)
        for point in forecast
    )
    humidity = _average(_humidity_score(point.humidity) for point in forecast)
    temperature = _average(_temperature_score(point.temperature) for point in forecast)
    wind = _average(_wind_score(point.wind_speed) for point in forecast)
    solar_adj = _average(_solar_adjustment(point) for point in forecast)

    score = rain * 0.40 + humidity * 0.25 + temperature * 0.20 + wind * 0.15 + solar_adj
    return round(max(0.0, min(score, 100.0)))


def calculate_estimated_drying_time(
    forecast: Sequence[LaundryForecastPoint],
    load_type: str = DEFAULT_LOAD_TYPE,
) -> float | None:
    """Estimate outdoor drying duration in hours based on forecast physics and load."""
    if not forecast:
        return None

    multiplier = LOAD_TYPE_MULTIPLIERS.get(load_type, 1.0)
    target_work = BASE_IDEAL_DRYING_HOURS * multiplier
    accumulated_work = 0.0
    elapsed_hours = 0.0

    for point in forecast:
        point_score = calculate_point_score(point)
        vpd = calculate_vpd_kpa(point.temperature, point.humidity, point.dew_point)
        vpd_factor = max(0.25, min(1.35, vpd / 1.25))
        hourly_rate = max(0.08, (point_score / 100.0) * vpd_factor)

        remaining = target_work - accumulated_work
        if hourly_rate >= remaining:
            elapsed_hours += remaining / hourly_rate
            return round(max(0.5, elapsed_hours), 1)

        accumulated_work += hourly_rate
        elapsed_hours += 1.0

    avg_rate = max(0.1, accumulated_work / len(forecast))
    remaining = max(0.0, target_work - accumulated_work)
    total_hours = elapsed_hours + (remaining / avg_rate)
    return round(min(48.0, max(0.5, total_hours)), 1)


def calculate_score_breakdown(
    forecast: Sequence[LaundryForecastPoint],
) -> LaundryScoreBreakdown:
    """Compute component scores, VPD, and hourly score curve for dashboards."""
    if not forecast:
        return LaundryScoreBreakdown(
            rain_score=0,
            humidity_score=0,
            temperature_score=0,
            wind_score=0,
            solar_score=0,
            vpd_kpa=0.0,
            hourly_scores=(),
        )

    rain = round(
        _average(
            _rain_score(point.precipitation_probability, point.condition)
            for point in forecast
        )
    )
    humidity = round(_average(_humidity_score(point.humidity) for point in forecast))
    temperature = round(
        _average(_temperature_score(point.temperature) for point in forecast)
    )
    wind = round(_average(_wind_score(point.wind_speed) for point in forecast))
    solar = round(_average(_solar_score(point) for point in forecast))
    vpd = round(
        _average(
            calculate_vpd_kpa(point.temperature, point.humidity, point.dew_point)
            for point in forecast
        ),
        2,
    )

    hourly_scores = tuple(
        {
            "datetime": point.datetime.isoformat(),
            "score": calculate_point_score(point),
            "suitable": _is_suitable_hour(point),
            "temperature": point.temperature,
            "humidity": point.humidity,
            "precipitation_probability": point.precipitation_probability,
            "wind_speed": point.wind_speed,
            "vpd_kpa": calculate_vpd_kpa(
                point.temperature, point.humidity, point.dew_point
            ),
        }
        for point in forecast
    )

    return LaundryScoreBreakdown(
        rain_score=rain,
        humidity_score=humidity,
        temperature_score=temperature,
        wind_score=wind,
        solar_score=solar,
        vpd_kpa=vpd,
        hourly_scores=hourly_scores,
    )


def calculate_drying_window(
    forecast: Sequence[LaundryForecastPoint],
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Find the longest continuous suitable drying window."""
    best_start: datetime | None = None
    best_end: datetime | None = None
    current_start: datetime | None = None
    current_end: datetime | None = None

    for point in forecast:
        if _is_suitable_hour(point):
            if current_end is not None and point.datetime > current_end:
                current_start = None
                current_end = None
            current_start = current_start or point.datetime
            current_end = point.datetime + timedelta(hours=1)
            if best_start is None or (
                current_end - current_start > cast(datetime, best_end) - best_start
            ):
                best_start = current_start
                best_end = current_end
        else:
            current_start = None
            current_end = None

    if best_start is None or best_end is None:
        return get_localized_strings(language).drying_window_none

    return f"{best_start:%H:%M}-{best_end:%H:%M}"


def status_from_index(
    index: int,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Map an index to the localized status string."""
    strings = get_localized_strings(language)
    if index >= 80:
        return strings.status_excellent
    if index >= 60:
        return strings.status_good
    if index >= 40:
        return strings.status_fair
    return strings.status_poor


def _tomorrow_forecast(
    forecast: Sequence[LaundryForecastPoint],
) -> tuple[LaundryForecastPoint, ...]:
    """Return forecast points for tomorrow's local date."""
    tomorrow = dt_util.now().date() + timedelta(days=1)
    return tuple(point for point in forecast if point.datetime.date() == tomorrow)


def build_recommendation(  # noqa: PLR0913
    *,
    index: int,
    status: str,
    forecast: Sequence[LaundryForecastPoint],
    drying_window: str,
    tomorrow_index: int | None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Build a short human-readable recommendation in the requested language."""
    strings = get_localized_strings(language)
    rain_after = _first_rain_time(forecast)

    if status in ALL_STATUS_EXCELLENT:
        recommendation = strings.rec_excellent
    elif status in ALL_STATUS_GOOD:
        recommendation = strings.rec_good
    elif status in ALL_STATUS_FAIR:
        recommendation = strings.rec_fair
    else:
        recommendation = strings.rec_poor

    if rain_after is not None and index >= 50:
        recommendation = strings.rec_rain_after.format(
            time=f"{rain_after:%H:%M}",
        )
    elif is_no_drying_window(drying_window):
        recommendation = strings.rec_no_window

    if (
        tomorrow_index is not None
        and tomorrow_index - index >= SIGNIFICANTLY_BETTER_DELTA
    ):
        separator = "" if recommendation.endswith("。") else " "
        recommendation = f"{recommendation}{separator}{strings.rec_tomorrow_better}"

    return recommendation


def _is_suitable_hour(point: LaundryForecastPoint) -> bool:
    """Return whether a forecast point is suitable for outdoor drying."""
    temp = point.temperature if point.temperature is not None else -999.0
    humidity = point.humidity if point.humidity is not None else 100.0
    precip = (
        point.precipitation_probability
        if point.precipitation_probability is not None
        else 100.0
    )
    wind = point.wind_speed if point.wind_speed is not None else 0.0
    return (
        temp >= 15.0
        and humidity <= 75.0
        and precip <= 20.0
        and wind >= 5.0
        and _dew_point_depression(point) >= 2.0
        and not _condition_is_rainy(point.condition)
    )


def _rain_score(probability: float | None, condition: str | None) -> float:
    """Score precipitation risk."""
    if _condition_is_rainy(condition):
        probability = max(probability or 0.0, 80.0)
    if probability is None:
        return 50.0
    return 100.0 - max(0.0, min(probability, 100.0))


def _humidity_score(humidity: float | None) -> float:
    """Score humidity with <=50% as ideal and 90% as minimum."""
    if humidity is None:
        return 50.0
    if humidity <= 50.0:
        return 100.0
    if humidity >= 90.0:
        return 0.0
    return (90.0 - humidity) / 40.0 * 100.0


def _temperature_score(temperature: float | None) -> float:
    """Score temperature with 22-32 C as ideal."""
    if temperature is None:
        return 50.0
    if 22.0 <= temperature <= 32.0:
        return 100.0
    if temperature < 10.0:
        return max(0.0, temperature / 10.0 * 35.0)
    if temperature < 22.0:
        return 35.0 + (temperature - 10.0) / 12.0 * 65.0
    if temperature <= 40.0:
        return 100.0 - (temperature - 32.0) / 8.0 * 20.0
    return max(50.0, 80.0 - (temperature - 40.0) * 2.0)


def _wind_score(wind_speed: float | None) -> float:
    """Score wind speed with 8-20 km/h as ideal."""
    if wind_speed is None:
        return 50.0
    if 8.0 <= wind_speed <= 20.0:
        return 100.0
    if wind_speed < 8.0:
        return max(0.0, wind_speed / 8.0 * 100.0)
    if wind_speed <= 40.0:
        return 100.0 - (wind_speed - 20.0) / 20.0 * 40.0
    return max(0.0, 60.0 - (wind_speed - 40.0) * 3.0)


def _first_rain_time(forecast: Sequence[LaundryForecastPoint]) -> datetime | None:
    """Return the first time rain is likely in the forecast."""
    for point in forecast:
        if (
            point.precipitation_probability is not None
            and point.precipitation_probability >= 50.0
        ) or _condition_is_rainy(point.condition):
            return point.datetime
    return None


def _condition_is_rainy(condition: str | None) -> bool:
    """Return whether a Home Assistant weather condition implies rain."""
    return condition in {
        "pouring",
        "rainy",
        "snowy",
        "snowy-rainy",
        "hail",
        "lightning-rainy",
    }


def _as_float(value: Any) -> float | None:
    """Convert a value to float if possible."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _average(values: Iterable[float]) -> float:
    """Return the average of generated score values."""
    score_values = list(values)
    if not score_values:
        return 0.0
    return sum(score_values) / len(score_values)
