"""Test package setup with Home Assistant mocks if not installed."""

import dataclasses
import sys
import typing
from datetime import timezone
from unittest.mock import MagicMock

if not hasattr(typing, "TypeAlias"):
    from typing_extensions import TypeAlias  # noqa: UP035

    typing.TypeAlias = TypeAlias  # type: ignore[attr-defined]

if sys.version_info < (3, 10):
    _orig_dataclass = dataclasses.dataclass

    def _compat_dataclass(*args, **kwargs):
        kwargs.pop("slots", None)
        kwargs.pop("kw_only", None)
        return _orig_dataclass(*args, **kwargs)

    dataclasses.dataclass = _compat_dataclass

if "homeassistant" not in sys.modules:
    for mod in [
        "homeassistant",
        "homeassistant.components",
        "homeassistant.components.weather",
        "homeassistant.components.sensor",
        "homeassistant.components.binary_sensor",
        "homeassistant.config_entries",
        "homeassistant.const",
        "homeassistant.core",
        "homeassistant.helpers",
        "homeassistant.helpers.device_registry",
        "homeassistant.helpers.entity",
        "homeassistant.helpers.entity_platform",
        "homeassistant.helpers.selector",
        "homeassistant.helpers.update_coordinator",
        "homeassistant.util",
        "homeassistant.util.dt",
        "homeassistant.util.unit_conversion",
    ]:
        if mod not in sys.modules:
            sys.modules[mod] = MagicMock()
        if "." in mod:
            parent_name, attr_name = mod.rsplit(".", 1)
            setattr(sys.modules[parent_name], attr_name, sys.modules[mod])

    # Configure specific mocked objects
    from datetime import datetime

    dt_mock = sys.modules["homeassistant.util.dt"]
    dt_mock.utcnow.side_effect = lambda: datetime.now(timezone.utc)
    dt_mock.now.side_effect = lambda: datetime.now(timezone.utc)
    dt_mock.as_local.side_effect = lambda d: d
    dt_mock.parse_datetime.side_effect = (
        lambda s: datetime.fromisoformat(s) if isinstance(s, str) else None
    )

    const_mock = sys.modules["homeassistant.const"]
    const_mock.ATTR_UNIT_OF_MEASUREMENT = "unit_of_measurement"

    class _Platform:
        WEATHER = "weather"
        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"

    class _UnitOfTemperature:
        CELSIUS = "°C"
        FAHRENHEIT = "°F"
        KELVIN = "K"

    class _UnitOfSpeed:
        KILOMETERS_PER_HOUR = "km/h"
        MILES_PER_HOUR = "mph"
        METERS_PER_SECOND = "m/s"
        KNOTS = "kn"
        FEET_PER_SECOND = "ft/s"

    const_mock.Platform = _Platform
    const_mock.UnitOfTemperature = _UnitOfTemperature
    const_mock.UnitOfSpeed = _UnitOfSpeed

    class _TemperatureConverter:
        @classmethod
        def convert(cls, value: float, from_unit: str, to_unit: str) -> float:
            if from_unit == to_unit:
                return value
            if from_unit == _UnitOfTemperature.FAHRENHEIT:
                celsius = (value - 32.0) * 5.0 / 9.0
            elif from_unit == _UnitOfTemperature.KELVIN:
                celsius = value - 273.15
            elif from_unit == _UnitOfTemperature.CELSIUS:
                celsius = value
            else:
                msg = f"Unsupported temperature unit: {from_unit}"
                raise ValueError(msg)
            if to_unit == _UnitOfTemperature.CELSIUS:
                return celsius
            if to_unit == _UnitOfTemperature.FAHRENHEIT:
                return celsius * 9.0 / 5.0 + 32.0
            if to_unit == _UnitOfTemperature.KELVIN:
                return celsius + 273.15
            msg = f"Unsupported temperature unit: {to_unit}"
            raise ValueError(msg)

    class _SpeedConverter:
        _TO_KMH: typing.ClassVar[dict[str, float]] = {
            _UnitOfSpeed.KILOMETERS_PER_HOUR: 1.0,
            _UnitOfSpeed.METERS_PER_SECOND: 3.6,
            _UnitOfSpeed.MILES_PER_HOUR: 1.609344,
            _UnitOfSpeed.KNOTS: 1.852,
            _UnitOfSpeed.FEET_PER_SECOND: 1.09728,
        }

        @classmethod
        def convert(cls, value: float, from_unit: str, to_unit: str) -> float:
            if from_unit == to_unit:
                return value
            if from_unit not in cls._TO_KMH or to_unit not in cls._TO_KMH:
                msg = f"Unsupported speed unit: {from_unit} -> {to_unit}"
                raise ValueError(msg)
            kmh = value * cls._TO_KMH[from_unit]
            return kmh / cls._TO_KMH[to_unit]

    unit_conv_mock = sys.modules["homeassistant.util.unit_conversion"]
    unit_conv_mock.TemperatureConverter = _TemperatureConverter
    unit_conv_mock.SpeedConverter = _SpeedConverter

    class _UpdateFailedError(Exception):
        """Mock UpdateFailed exception."""

    class _DataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

        def __init__(
            self,
            hass,
            logger,
            *,
            name,
            update_interval=None,
            config_entry=None,
        ):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.config_entry = config_entry

    coord_mock = sys.modules["homeassistant.helpers.update_coordinator"]
    coord_mock.DataUpdateCoordinator = _DataUpdateCoordinator
    coord_mock.UpdateFailed = _UpdateFailedError

    core_mock = sys.modules["homeassistant.core"]
    core_mock.callback = lambda fn: fn

    class _ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

        async def async_set_unique_id(self, unique_id):
            self._unique_id = unique_id

        def _abort_if_unique_id_configured(self):
            pass

        def async_create_entry(self, *, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(self, *, step_id, data_schema=None, errors=None):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
            }

    class _OptionsFlow:
        def async_create_entry(self, *, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(self, *, step_id, data_schema=None, errors=None):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
            }

    ce_mock = sys.modules["homeassistant.config_entries"]
    ce_mock.ConfigFlow = _ConfigFlow
    ce_mock.OptionsFlow = _OptionsFlow
