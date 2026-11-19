# Laundry Advisor

[![Home Assistant Marketplace](https://img.shields.io/badge/Home%20Assistant-Marketplace-41BDF5.svg)](https://github.com/hacs/default)
[![Marketplace validation](https://github.com/Lean724/Laundry-Advisor/actions/workflows/hacs.yml/badge.svg)](https://github.com/Lean724/Laundry-Advisor/actions/workflows/hacs.yml)
[![Hassfest](https://github.com/Lean724/Laundry-Advisor/actions/workflows/hassfest.yml/badge.svg)](https://github.com/Lean724/Laundry-Advisor/actions/workflows/hassfest.yml)

Laundry Advisor is a **Home Assistant laundry advisor integration** that analyzes weather forecasts and optional real-time outdoor sensors to recommend the best time to wash clothes and dry laundry outdoors. It combines a laundry weather forecast, outdoor drying conditions, and local sensor data in one Home Assistant integration.

It works with any `weather.*` entity that supports Home Assistant's modern
forecast APIs. The integration is available directly in the Home Assistant
**Marketplace** (formerly HACS) and follows modern Home Assistant patterns:
Config Flow, `DataUpdateCoordinator`, diagnostics, translations, `DeviceInfo`,
entity descriptions, unit conversion, async-first code, and typed Python.

## Architecture Design

Laundry Advisor is built around a single config entry and a single
`LaundryAdvisorCoordinator`. During setup, the Config Flow asks the user to
select a `weather.*` entity, forecast horizon, update interval, laundry load
type, and optional local outdoor sensors (temperature, humidity, and wind
speed). These values are stored in the config entry and can be updated at any
time from the integration options flow.

The coordinator is the only component that talks to Home Assistant weather
forecast APIs. It uses the official `weather.get_forecasts` action and requests
hourly forecast data first. If the selected weather provider does not expose
hourly forecasts, it falls back to daily forecast data and expands each daily
point into hourly-like points so the same scoring engine can still run. Forecast
and local sensor values are automatically normalized to Celsius (`°C`) and
`km/h` using Home Assistant's unit converters before scoring.

Forecast data is normalized into `LaundryForecastPoint` objects containing local
datetime, temperature, humidity, precipitation probability, wind speed,
condition, dew point, UV index, cloud coverage, and daytime state. The scoring
engine calculates a 0–100 Laundry Index using weighted factors (rain 40%,
humidity 25%, temperature 20%, and wind 15%) refined with Vapor Pressure Deficit
(VPD), dew point depression, UV/cloud cover, and nighttime adjustments.

The drying window calculation scans the configured horizon and finds the longest
continuous sequence where temperature, humidity, rain probability, wind, and dew
point depression all meet outdoor drying thresholds. The recommendation
generator combines the index band, rain risk, drying window, and tomorrow
comparison into a concise localized message.

## Entities

Laundry Advisor creates these entities:

| Entity | Type | Example value |
| --- | --- | --- |
| `sensor.laundry_index` | Sensor | `84 %` |
| `sensor.laundry_status` | Sensor | `Excellent` |
| `sensor.laundry_recommendation` | Sensor | `Excellent drying conditions today.` |
| `sensor.laundry_drying_window` | Sensor | `09:00-17:00` |
| `sensor.laundry_estimated_drying_time` | Sensor | `2.8 h` |
| `binary_sensor.laundry_good_day` | Binary sensor | `on` |

`sensor.laundry_index` also exposes rich `extra_state_attributes` for dashboard
cards (such as `ApexCharts` or `Mushroom`): `rain_score`, `humidity_score`,
`temperature_score`, `wind_score`, `solar_score`, `vpd_kpa`, `tomorrow_index`,
`load_type`, `estimated_drying_time`, and the hour-by-hour `hourly_scores`
curve.

Status bands:

| Index | Status |
| --- | --- |
| `0-39` | Poor |
| `40-59` | Fair |
| `60-79` | Good |
| `80-100` | Excellent |

## Calculation

Laundry Index uses a 0–100 scale:

| Factor | Weight | Rule |
| --- | --- | --- |
| Rain | 40% | 0% rain gives max score, 100% rain gives zero |
| Humidity | 25% | <=50% is ideal, 90% is minimum |
| Temperature | 20% | 22–32 °C is ideal, cold is heavily penalized |
| Wind | 15% | 8–20 km/h is ideal, calm and very strong wind are penalized |
| Solar / VPD | Adjustment | UV index, cloud coverage, nighttime penalty, and condensation check |

An hour is suitable for drying when:

- Temperature is at least 15 °C.
- Humidity is at most 75%.
- Rain probability is at most 20%.
- Wind is at least 5 km/h.
- Dew point depression ($T - T_d$) is at least 2 °C.
- The weather condition is not rain, snow, hail, or storm rain.

## Installation

### Home Assistant Marketplace (Recommended)

[![Open your Home Assistant instance and open Laundry Advisor in the Marketplace.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Lean724&repository=Laundry-Advisor&category=integration)

1. In Home Assistant, go to **Settings > Marketplace** (or open **HACS** on Home Assistant 2026.1–2026.10).
2. Search for **Laundry Advisor** and select it.
3. Click **Install** (or **Download** in legacy HACS) and follow the on-screen prompts to complete the configuration flow.

### Manual installation

Copy the integration folder into your Home Assistant config directory:

```text
config/custom_components/laundry_advisor
```

Restart Home Assistant, then go to **Settings > Devices & services > Add integration** and search for **Laundry Advisor**.

## Configuration

The Config Flow and Options Flow let you configure:

- **Weather entity**, for example `weather.forecast_home`.
- **Forecast horizon**, default `12` hours (`3–48` hours).
- **Update interval**, default `30` minutes (`5–240` minutes).
- **Laundry load type**: Light / Synthetics, Standard / Cotton (default), or Heavy / Towels & Jeans.
- **Local outdoor sensors (optional)**: Real-time outdoor temperature, humidity, and wind speed sensors to refine the current hour.

The selected weather entity must expose Home Assistant forecast support. Hourly
forecasts are preferred; daily forecasts are used as a fallback.

## Supported Languages

Configuration and options flows, selectors, entity names, and sensor responses
(`laundry_status`, `laundry_recommendation`, and `laundry_drying_window`) are
localized in:

- English (`en`)
- Spanish (`es`)
- Italian (`it`)
- Portuguese (`pt`, `pt-BR`)
- Russian (`ru`)
- German (`de`)
- French (`fr`)
- Simplified Chinese (`zh-Hans`)

## Diagnostics

Diagnostics expose non-sensitive integration state:

```json
{
  "weather_entity": "weather.forecast_home",
  "forecast_hours": 12,
  "load_type": "standard",
  "latest_index": 84,
  "drying_window": "09:00-17:00",
  "estimated_drying_time": 2.8,
  "status": "Excellent",
  "tomorrow_index": 78,
  "breakdown": {
    "rain_score": 100,
    "humidity_score": 88,
    "temperature_score": 92,
    "wind_score": 95,
    "solar_score": 90,
    "vpd_kpa": 1.65
  }
}
```

## Development

Install development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run local checks:

```bash
ruff check .
mypy custom_components/laundry_advisor
pytest -q
```

Hassfest and Marketplace validation run in GitHub Actions.

## Compatibility

- Home Assistant 2026+
- Home Assistant Marketplace (formerly HACS)
- Python versions supported by current Home Assistant

## License

MIT
