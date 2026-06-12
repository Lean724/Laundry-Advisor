# Laundry Advisor

[![HACS validation](https://github.com/Lean724/Laundry-Advisor/actions/workflows/hacs.yml/badge.svg)](https://github.com/Lean724/Laundry-Advisor/actions/workflows/hacs.yml)
[![Hassfest](https://github.com/Lean724/Laundry-Advisor/actions/workflows/hassfest.yml/badge.svg)](https://github.com/Lean724/Laundry-Advisor/actions/workflows/hassfest.yml)

Laundry Advisor is a Home Assistant custom integration that analyzes weather
forecasts and recommends whether it is a good moment to wash clothes and dry
them outdoors.

It works with any `weather.*` entity that supports Home Assistant's modern
forecast APIs. The integration is designed for HACS distribution and follows
modern Home Assistant patterns: Config Flow, `DataUpdateCoordinator`,
diagnostics, translations, `DeviceInfo`, entity descriptions, async-first code,
and typed Python.

## Architecture Design

Laundry Advisor is built around a single config entry and a single
`LaundryAdvisorCoordinator`. During setup, the Config Flow asks the user to
select a `weather.*` entity and configure two numeric options: forecast horizon
and update interval. These values are stored in the config entry and can be
changed later from the integration options flow.

The coordinator is the only component that talks to Home Assistant weather
forecast APIs. It uses the current `homeassistant.components.weather`
`async_get_forecasts` helper and requests hourly forecast data first. If the
selected weather provider does not expose hourly forecasts, it falls back to
daily forecast data and expands each daily point into hourly-like points so the
same scoring engine can still run. The integration intentionally does not read
legacy `forecast` attributes from the weather entity state.

Forecast data is normalized into `LaundryForecastPoint` objects containing local
datetime, temperature, humidity, precipitation probability, wind speed, and
condition. The scoring engine is implemented as pure functions so it is easy to
test and evolve. It calculates a 0-100 Laundry Index using the requested
weights: rain 40%, humidity 25%, temperature 20%, and wind 15%.

The drying window calculation scans the configured horizon and finds the longest
continuous sequence where temperature, humidity, rain probability, and wind all
meet the outdoor drying thresholds. The recommendation generator combines the
index band, rain risk, drying window, and tomorrow comparison into a concise
human-readable message.

Entities are deliberately thin. Sensors and binary sensors read already computed
data from the coordinator, expose shared `DeviceInfo`, and use entity
descriptions with translation keys. Diagnostics also read from the coordinator,
returning only operational state such as selected weather entity, forecast
horizon, latest index, and drying window.

For future Energy Awareness features, `coordinator.py` includes a protocol-based
extension point for context providers. Future releases can add solar production,
electric tariffs, dryer integration, washing machine state, and occupancy
without changing the entity layer or the core forecast retrieval path.

## Entities

Laundry Advisor creates these entities:

| Entity | Type | Example value |
| --- | --- | --- |
| `sensor.laundry_index` | Sensor | `84 %` |
| `sensor.laundry_status` | Sensor | `Excellent` |
| `sensor.laundry_recommendation` | Sensor | `Excellent drying conditions today.` |
| `sensor.laundry_drying_window` | Sensor | `09:00-17:00` |
| `binary_sensor.laundry_good_day` | Binary sensor | `on` |

Status bands:

| Index | Status |
| --- | --- |
| `0-39` | Poor |
| `40-59` | Fair |
| `60-79` | Good |
| `80-100` | Excellent |

## Calculation

Laundry Index uses a 0-100 scale:

| Factor | Weight | Rule |
| --- | --- | --- |
| Rain | 40% | 0% rain gives max score, 100% rain gives zero |
| Humidity | 25% | <=50% is ideal, 90% is minimum |
| Temperature | 20% | 22-32 C is ideal, cold is heavily penalized |
| Wind | 15% | 8-20 km/h is ideal, calm and very strong wind are penalized |

An hour is suitable for drying when:

- Temperature is at least 15 C.
- Humidity is at most 75%.
- Rain probability is at most 20%.
- Wind is at least 5 km/h.
- The weather condition is not rain, snow, hail, or storm rain.

## Installation

### HACS custom repository

[![Open your Home Assistant instance and add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Lean724&repository=Laundry-Advisor&category=integration)

1. Open HACS.
2. Go to **Integrations**.
3. Open the menu and choose **Custom repositories**.
4. Add this repository URL.
5. Select category **Integration**.
6. Install **Laundry Advisor**.
7. Restart Home Assistant.
8. Go to **Settings > Devices & services > Add integration**.
9. Search for **Laundry Advisor**.

### Manual installation

Copy the integration folder into your Home Assistant config directory:

```text
config/custom_components/laundry_advisor
```

Restart Home Assistant, then add the integration from the UI.

## Configuration

The Config Flow lets you select:

- Weather entity, for example `weather.forecast_home`.
- Forecast horizon, default `12` hours.
- Update interval, default `30` minutes.

The selected weather entity must expose Home Assistant forecast support. Hourly
forecasts are preferred; daily forecasts are used as a fallback.

## Diagnostics

Diagnostics expose non-sensitive integration state:

```json
{
  "weather_entity": "weather.forecast_home",
  "forecast_hours": 12,
  "latest_index": 84,
  "drying_window": "09:00-17:00"
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
```

Hassfest runs in GitHub Actions.

## Compatibility

- Home Assistant 2026+
- HACS custom repository layout
- Python versions supported by current Home Assistant

## License

MIT
