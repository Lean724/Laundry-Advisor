"""Tests for Laundry Advisor calculation engine."""

# Pre-import test environment mocks
import tests  # noqa: F401, I001
from datetime import datetime, timedelta, timezone
import unittest

from custom_components.laundry_advisor.const import (
    DRYING_WINDOW_NONE,
    STATUS_EXCELLENT,
    STATUS_FAIR,
    STATUS_GOOD,
    STATUS_POOR,
)
from custom_components.laundry_advisor.coordinator import (
    LaundryForecastPoint,
    build_recommendation,
    calculate_drying_window,
    calculate_laundry_index,
    status_from_index,
)


class TestLaundryAdvisorEngine(unittest.TestCase):
    """Test calculation functions in coordinator."""

    def setUp(self) -> None:
        """Set up base timestamps."""
        self.base_time = datetime(2026, 11, 7, 8, 0, tzinfo=timezone.utc)

    def test_empty_forecast(self) -> None:
        """Test with empty forecast."""
        self.assertEqual(calculate_laundry_index(()), 0)
        self.assertEqual(calculate_drying_window(()), DRYING_WINDOW_NONE)

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


if __name__ == "__main__":
    unittest.main()
