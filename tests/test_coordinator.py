"""Tests for Laundry Advisor calculation engine and localization."""

# Pre-import test environment mocks
import tests  # noqa: F401, I001
import asyncio
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    UnitOfSpeed,
    UnitOfTemperature,
)

from custom_components.laundry_advisor.config_flow import LaundryAdvisorOptionsFlow
from custom_components.laundry_advisor.const import (
    CONF_FORECAST_HOURS,
    CONF_HUMIDITY_SENSOR,
    CONF_LOAD_TYPE,
    CONF_TEMP_SENSOR,
    CONF_UPDATE_INTERVAL,
    CONF_WEATHER_ENTITY,
    CONF_WIND_SENSOR,
    DRYING_WINDOW_NONE,
    LOAD_TYPE_HEAVY,
    LOAD_TYPE_LIGHT,
    LOAD_TYPE_STANDARD,
    STATUS_EXCELLENT,
    STATUS_FAIR,
    STATUS_GOOD,
    STATUS_POOR,
    SUPPORTED_LANGUAGES,
)
from custom_components.laundry_advisor.coordinator import (
    LaundryAdvisorCoordinator,
    LaundryForecastPoint,
    _normalize_forecast_point,
    apply_local_overrides,
    build_recommendation,
    calculate_drying_window,
    calculate_estimated_drying_time,
    calculate_laundry_index,
    calculate_score_breakdown,
    calculate_vpd_kpa,
    status_from_index,
)
from custom_components.laundry_advisor.localization import (
    LOCALIZED_STRINGS,
    get_localized_strings,
    is_no_drying_window,
    normalize_language,
)


def _collect_keys(data: dict, prefix: str = "") -> set[str]:
    """Recursively collect all key paths in a JSON dictionary."""
    keys: set[str] = set()
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.add(full_key)
        if isinstance(value, dict):
            keys.update(_collect_keys(value, full_key))
    return keys


class TestLaundryAdvisorEngine(unittest.TestCase):
    """Test calculation functions in coordinator."""

    def setUp(self) -> None:
        """Set up base timestamps."""
        self.base_time = datetime(2026, 11, 7, 8, 0, tzinfo=timezone.utc)

    def test_empty_forecast(self) -> None:
        """Test with empty forecast."""
        self.assertEqual(calculate_laundry_index(()), 0)
        self.assertEqual(calculate_drying_window(()), DRYING_WINDOW_NONE)
        self.assertIsNone(calculate_estimated_drying_time(()))

    def test_ideal_conditions(self) -> None:
        """Test ideal drying conditions score near 100."""
        points = [
            LaundryForecastPoint(
                datetime=self.base_time + timedelta(hours=i),
                temperature=25.0,
                humidity=45.0,
                precipitation_probability=0.0,
                wind_speed=15.0,
                condition="sunny",
            )
            for i in range(8)
        ]
        score = calculate_laundry_index(points)
        self.assertEqual(score, 100)
        self.assertEqual(status_from_index(score), STATUS_EXCELLENT)
        window = calculate_drying_window(points)
        self.assertEqual(window, "08:00-16:00")

    def test_poor_conditions_rain(self) -> None:
        """Test rainy conditions yield a poor score."""
        points = [
            LaundryForecastPoint(
                datetime=self.base_time + timedelta(hours=i),
                temperature=12.0,
                humidity=95.0,
                precipitation_probability=80.0,
                wind_speed=2.0,
                condition="rainy",
            )
            for i in range(6)
        ]
        score = calculate_laundry_index(points)
        self.assertLess(score, 40)
        self.assertEqual(status_from_index(score), STATUS_POOR)
        self.assertEqual(calculate_drying_window(points), DRYING_WINDOW_NONE)

    def test_status_bands(self) -> None:
        """Verify status band thresholds."""
        self.assertEqual(status_from_index(85), STATUS_EXCELLENT)
        self.assertEqual(status_from_index(80), STATUS_EXCELLENT)
        self.assertEqual(status_from_index(79), STATUS_GOOD)
        self.assertEqual(status_from_index(60), STATUS_GOOD)
        self.assertEqual(status_from_index(59), STATUS_FAIR)
        self.assertEqual(status_from_index(40), STATUS_FAIR)
        self.assertEqual(status_from_index(39), STATUS_POOR)
        self.assertEqual(status_from_index(0), STATUS_POOR)

    def test_drying_window_gap(self) -> None:
        """Verify drying window properly detects non-consecutive hours."""
        points = [
            LaundryForecastPoint(
                datetime=self.base_time,  # 08:00
                temperature=25.0,
                humidity=45.0,
                precipitation_probability=0.0,
                wind_speed=15.0,
                condition="sunny",
            ),
            # Gap of 3 hours, then two consecutive hours: 12:00 and 13:00
            LaundryForecastPoint(
                datetime=self.base_time + timedelta(hours=4),  # 12:00
                temperature=25.0,
                humidity=45.0,
                precipitation_probability=0.0,
                wind_speed=15.0,
                condition="sunny",
            ),
            LaundryForecastPoint(
                datetime=self.base_time + timedelta(hours=5),  # 13:00
                temperature=25.0,
                humidity=45.0,
                precipitation_probability=0.0,
                wind_speed=15.0,
                condition="sunny",
            ),
        ]
        window = calculate_drying_window(points)
        self.assertEqual(window, "12:00-14:00")

    def test_recommendation_rain_warning(self) -> None:
        """Test rain warning in recommendation when rain is expected."""
        points = [
            LaundryForecastPoint(
                datetime=self.base_time + timedelta(hours=i),
                temperature=24.0,
                humidity=50.0,
                precipitation_probability=60.0 if i >= 4 else 5.0,
                wind_speed=12.0,
                condition="rainy" if i >= 4 else "sunny",
            )
            for i in range(8)
        ]
        rec = build_recommendation(
            index=65,
            status=STATUS_GOOD,
            forecast=points,
            drying_window="08:00-12:00",
            tomorrow_index=None,
        )
        self.assertIn("rain is expected after 12:00", rec)

    def test_recommendation_tomorrow_better(self) -> None:
        """Test tomorrow comparison recommendation."""
        points = [
            LaundryForecastPoint(
                datetime=self.base_time + timedelta(hours=i),
                temperature=20.0,
                humidity=60.0,
                precipitation_probability=10.0,
                wind_speed=10.0,
                condition="cloudy",
            )
            for i in range(6)
        ]
        rec = build_recommendation(
            index=55,
            status=STATUS_FAIR,
            forecast=points,
            drying_window="08:00-14:00",
            tomorrow_index=80,
        )
        self.assertIn("Tomorrow offers substantially better drying conditions.", rec)

    def test_vpd_and_solar_physics(self) -> None:
        """Test VPD calculation and solar/nighttime/dew-point adjustments."""
        vpd_hot_dry = calculate_vpd_kpa(30.0, 35.0)
        vpd_cool_humid = calculate_vpd_kpa(15.0, 85.0)
        self.assertGreater(vpd_hot_dry, 2.0)
        self.assertLess(vpd_cool_humid, 0.5)

        day_point = LaundryForecastPoint(
            datetime=self.base_time,
            temperature=20.0,
            humidity=60.0,
            precipitation_probability=10.0,
            wind_speed=10.0,
            condition="sunny",
            uv_index=7.0,
            is_daytime=True,
        )
        night_point = LaundryForecastPoint(
            datetime=self.base_time,
            temperature=20.0,
            humidity=60.0,
            precipitation_probability=10.0,
            wind_speed=10.0,
            condition="clear-night",
            uv_index=0.0,
            is_daytime=False,
        )
        self.assertGreater(
            calculate_laundry_index([day_point]),
            calculate_laundry_index([night_point]),
        )

    def test_estimated_drying_time_by_load_type(self) -> None:
        """Test estimated drying time across light, standard, and heavy loads."""
        points = [
            LaundryForecastPoint(
                datetime=self.base_time + timedelta(hours=i),
                temperature=26.0,
                humidity=45.0,
                precipitation_probability=0.0,
                wind_speed=14.0,
                condition="sunny",
            )
            for i in range(10)
        ]
        light_time = calculate_estimated_drying_time(points, LOAD_TYPE_LIGHT)
        standard_time = calculate_estimated_drying_time(points, LOAD_TYPE_STANDARD)
        heavy_time = calculate_estimated_drying_time(points, LOAD_TYPE_HEAVY)

        self.assertIsNotNone(light_time)
        self.assertIsNotNone(standard_time)
        self.assertIsNotNone(heavy_time)
        assert light_time is not None
        assert standard_time is not None
        assert heavy_time is not None
        self.assertLess(light_time, standard_time)
        self.assertLess(standard_time, heavy_time)

    def test_local_sensor_overrides_and_breakdown(self) -> None:
        """Test local outdoor sensor overrides and dashboard breakdown attributes."""
        points = [
            LaundryForecastPoint(
                datetime=self.base_time + timedelta(hours=i),
                temperature=20.0,
                humidity=65.0,
                precipitation_probability=10.0,
                wind_speed=8.0,
                condition="partlycloudy",
            )
            for i in range(4)
        ]
        overridden = apply_local_overrides(
            points,
            temperature=28.5,
            humidity=40.0,
            wind_speed=16.0,
        )
        self.assertEqual(overridden[0].temperature, 28.5)
        self.assertEqual(overridden[0].humidity, 40.0)
        self.assertEqual(overridden[0].wind_speed, 16.0)
        self.assertEqual(overridden[1].temperature, 20.0)

        breakdown = calculate_score_breakdown(overridden)
        self.assertEqual(len(breakdown.hourly_scores), 4)
        self.assertGreater(breakdown.vpd_kpa, 0.0)
        self.assertIn("score", breakdown.hourly_scores[0])
        self.assertIn("vpd_kpa", breakdown.hourly_scores[0])

    def test_language_normalization(self) -> None:
        """Test normalization of Home Assistant language codes."""
        self.assertEqual(normalize_language("it"), "it")
        self.assertEqual(normalize_language("it-IT"), "it")
        self.assertEqual(normalize_language("en-US"), "en")
        self.assertEqual(normalize_language("es-AR"), "es")
        self.assertEqual(normalize_language("pt-BR"), "pt")
        self.assertEqual(normalize_language("ru-RU"), "ru")
        self.assertEqual(normalize_language("de-DE"), "de")
        self.assertEqual(normalize_language("fr-FR"), "fr")
        self.assertEqual(normalize_language("zh-Hans"), "zh-Hans")
        self.assertEqual(normalize_language("zh-CN"), "zh-Hans")
        self.assertEqual(normalize_language("zh_CN"), "zh-Hans")
        self.assertEqual(normalize_language("unknown"), "en")
        self.assertEqual(normalize_language(None), "en")

    def test_localized_sensor_responses_all_languages(self) -> None:
        """Test localized sensor responses across all 8 required languages."""
        rain_points = [
            LaundryForecastPoint(
                datetime=self.base_time + timedelta(hours=i),
                temperature=24.0,
                humidity=50.0,
                precipitation_probability=60.0 if i >= 4 else 5.0,
                wind_speed=12.0,
                condition="rainy" if i >= 4 else "sunny",
            )
            for i in range(8)
        ]

        for lang in SUPPORTED_LANGUAGES:
            strings = get_localized_strings(lang)

            # Status localization
            self.assertEqual(status_from_index(85, lang), strings.status_excellent)
            self.assertEqual(status_from_index(65, lang), strings.status_good)
            self.assertEqual(status_from_index(45, lang), strings.status_fair)
            self.assertEqual(status_from_index(20, lang), strings.status_poor)

            # Drying window localization when no suitable window exists
            no_window = calculate_drying_window((), lang)
            self.assertEqual(no_window, strings.drying_window_none)
            self.assertTrue(is_no_drying_window(no_window))

            # Recommendation localization with rain time and tomorrow comparison
            rec = build_recommendation(
                index=65,
                status=strings.status_good,
                forecast=rain_points,
                drying_window="08:00-12:00",
                tomorrow_index=85,
                language=lang,
            )
            self.assertIn("12:00", rec)
            self.assertIn(strings.rec_tomorrow_better, rec)

            # Recommendation when no drying window is available
            rec_none = build_recommendation(
                index=30,
                status=strings.status_poor,
                forecast=(),
                drying_window=no_window,
                tomorrow_index=None,
                language=lang,
            )
            self.assertEqual(rec_none, strings.rec_no_window)

    def test_translation_files_match_strings_json(self) -> None:
        """Verify all translation JSON files exist and match strings.json keys."""
        base_dir = (
            Path(__file__).resolve().parent.parent
            / "custom_components"
            / "laundry_advisor"
        )
        strings_path = base_dir / "strings.json"
        translations_dir = base_dir / "translations"

        with strings_path.open(encoding="utf-8") as f:
            strings_data = json.load(f)
        expected_keys = _collect_keys(strings_data)

        required_files = [
            "en.json",
            "es.json",
            "it.json",
            "pt.json",
            "pt-BR.json",
            "ru.json",
            "de.json",
            "fr.json",
            "zh-Hans.json",
        ]
        for filename in required_files:
            file_path = translations_dir / filename
            self.assertTrue(file_path.exists(), f"Missing translation file: {filename}")
            with file_path.open(encoding="utf-8") as f:
                trans_data = json.load(f)
            self.assertEqual(
                _collect_keys(trans_data),
                expected_keys,
                f"Key mismatch in {filename}",
            )

        self.assertEqual(set(LOCALIZED_STRINGS.keys()), set(SUPPORTED_LANGUAGES))

    def test_options_flow_can_clear_optional_sensors(self) -> None:
        """Verify optional sensors chosen during setup can be unset in options."""
        entry = SimpleNamespace(
            data={
                CONF_WEATHER_ENTITY: "weather.home",
                CONF_FORECAST_HOURS: 12,
                CONF_UPDATE_INTERVAL: 30,
                CONF_LOAD_TYPE: LOAD_TYPE_STANDARD,
                CONF_TEMP_SENSOR: "sensor.outdoor_temp",
                CONF_HUMIDITY_SENSOR: "sensor.outdoor_humidity",
                CONF_WIND_SENSOR: "sensor.outdoor_wind",
            },
            options={},
        )

        hass = MagicMock()
        hass.states.get.return_value = SimpleNamespace(name="Home Weather")

        flow = LaundryAdvisorOptionsFlow(entry)  # type: ignore[arg-type]
        flow.hass = hass

        result = asyncio.run(
            flow.async_step_init(
                {
                    CONF_WEATHER_ENTITY: "weather.home",
                    CONF_FORECAST_HOURS: 12,
                    CONF_UPDATE_INTERVAL: 30,
                    CONF_LOAD_TYPE: LOAD_TYPE_STANDARD,
                }
            )
        )

        self.assertEqual(result["type"], "create_entry")
        options_data = result["data"]
        self.assertIsNone(options_data[CONF_TEMP_SENSOR])
        self.assertIsNone(options_data[CONF_HUMIDITY_SENSOR])
        self.assertIsNone(options_data[CONF_WIND_SENSOR])

        entry.options = options_data
        coordinator = LaundryAdvisorCoordinator(hass, entry)  # type: ignore[arg-type]
        self.assertIsNone(coordinator._get_option_or_data(CONF_TEMP_SENSOR))  # noqa: SLF001
        self.assertIsNone(coordinator._get_option_or_data(CONF_HUMIDITY_SENSOR))  # noqa: SLF001
        self.assertIsNone(coordinator._get_option_or_data(CONF_WIND_SENSOR))  # noqa: SLF001

    def test_forecast_unit_conversion_imperial_and_metric(self) -> None:
        """Verify imperial forecast values are converted to Celsius and km/h."""
        raw_imperial = {
            "datetime": "2026-11-07T08:00:00+00:00",
            "temperature": 70.0,  # 21.11 C
            "dew_point": 50.0,  # 10.0 C
            "humidity": 50.0,
            "precipitation_probability": 5.0,
            "wind_speed": 10.0,  # 16.09344 km/h
            "condition": "sunny",
        }
        point_imp = _normalize_forecast_point(
            raw_imperial,  # type: ignore[arg-type]
            temperature_unit=UnitOfTemperature.FAHRENHEIT,
            wind_speed_unit=UnitOfSpeed.MILES_PER_HOUR,
        )
        assert point_imp.temperature is not None
        assert point_imp.dew_point is not None
        assert point_imp.wind_speed is not None
        self.assertAlmostEqual(point_imp.temperature, 21.1111, places=3)
        self.assertAlmostEqual(point_imp.dew_point, 10.0, places=3)
        self.assertAlmostEqual(point_imp.wind_speed, 16.09344, places=3)

        raw_metric = {
            "datetime": "2026-11-07T08:00:00+00:00",
            "temperature": point_imp.temperature,
            "dew_point": point_imp.dew_point,
            "humidity": 50.0,
            "precipitation_probability": 5.0,
            "wind_speed": point_imp.wind_speed,
            "condition": "sunny",
        }
        point_met = _normalize_forecast_point(
            raw_metric,  # type: ignore[arg-type]
            temperature_unit=UnitOfTemperature.CELSIUS,
            wind_speed_unit=UnitOfSpeed.KILOMETERS_PER_HOUR,
        )

        self.assertEqual(
            calculate_laundry_index([point_imp]),
            calculate_laundry_index([point_met]),
        )
        self.assertEqual(
            calculate_drying_window([point_imp]),
            calculate_drying_window([point_met]),
        )

    def test_coordinator_converts_forecast_and_local_sensors(self) -> None:
        """Verify coordinator converts forecast and local sensor units."""
        entry = SimpleNamespace(
            data={
                CONF_WEATHER_ENTITY: "weather.home",
                CONF_FORECAST_HOURS: 4,
                CONF_UPDATE_INTERVAL: 30,
                CONF_LOAD_TYPE: LOAD_TYPE_STANDARD,
                CONF_TEMP_SENSOR: "sensor.local_temp_f",
                CONF_HUMIDITY_SENSOR: "sensor.local_humidity",
                CONF_WIND_SENSOR: "sensor.local_wind_mph",
            },
            options={},
        )

        sensor_states = {
            "sensor.local_temp_f": SimpleNamespace(
                state="77.0",  # 25.0 C
                attributes={ATTR_UNIT_OF_MEASUREMENT: UnitOfTemperature.FAHRENHEIT},
            ),
            "sensor.local_humidity": SimpleNamespace(
                state="45.0",
                attributes={ATTR_UNIT_OF_MEASUREMENT: "%"},
            ),
            "sensor.local_wind_mph": SimpleNamespace(
                state="10.0",  # 16.09344 km/h
                attributes={ATTR_UNIT_OF_MEASUREMENT: UnitOfSpeed.MILES_PER_HOUR},
            ),
        }

        hass = MagicMock()
        hass.config = SimpleNamespace(
            language="en",
            units=SimpleNamespace(
                temperature_unit=UnitOfTemperature.FAHRENHEIT,
                wind_speed_unit=UnitOfSpeed.MILES_PER_HOUR,
            ),
        )
        hass.states.get.side_effect = sensor_states.get
        hass.services.async_call = AsyncMock(
            return_value={
                "weather.home": {
                    "forecast": [
                        {
                            "datetime": (
                                self.base_time + timedelta(hours=i)
                            ).isoformat(),
                            "temperature": 70.0,  # 21.11 C
                            "dew_point": 50.0,  # 10.0 C
                            "humidity": 50.0,
                            "precipitation_probability": 0.0,
                            "wind_speed": 10.0,  # 16.09 km/h
                            "condition": "sunny",
                        }
                        for i in range(4)
                    ]
                }
            }
        )

        coordinator = LaundryAdvisorCoordinator(hass, entry)  # type: ignore[arg-type]
        data = asyncio.run(coordinator._async_update_data())  # noqa: SLF001

        assert data.forecast[0].temperature is not None
        assert data.forecast[0].wind_speed is not None
        assert data.forecast[1].temperature is not None
        self.assertAlmostEqual(data.forecast[0].temperature, 25.0, places=3)
        self.assertAlmostEqual(data.forecast[0].wind_speed, 16.09344, places=3)
        self.assertAlmostEqual(data.forecast[1].temperature, 21.1111, places=3)
        self.assertTrue(data.good_day)
        self.assertEqual(data.drying_window, "08:00-12:00")


if __name__ == "__main__":
    unittest.main()
