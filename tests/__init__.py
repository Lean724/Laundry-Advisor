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
    ]:
        if mod not in sys.modules:
            sys.modules[mod] = MagicMock()

    # Configure specific mocked objects
    from datetime import datetime

    dt_mock = sys.modules["homeassistant.util.dt"]
    dt_mock.utcnow.side_effect = lambda: datetime.now(timezone.utc)
    dt_mock.now.side_effect = lambda: datetime.now(timezone.utc)
    dt_mock.as_local.side_effect = lambda d: d
    dt_mock.parse_datetime.side_effect = (
        lambda s: datetime.fromisoformat(s) if isinstance(s, str) else None
    )
