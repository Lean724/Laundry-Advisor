"""Tests for Laundry Advisor calculation engine and localization."""

# Pre-import test environment mocks
import tests  # noqa: F401, I001
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from custom_components.laundry_advisor.const import (
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
    LaundryForecastPoint,
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


if __name__ == "__main__":
    unittest.main()
