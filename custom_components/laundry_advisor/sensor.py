"""Sensor platform for Laundry Advisor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LaundryAdvisorConfigEntry
from .const import (
    ATTR_ESTIMATED_DRYING_TIME,
    ATTR_HOURLY_SCORES,
    ATTR_HUMIDITY_SCORE,
    ATTR_LOAD_TYPE,
    ATTR_RAIN_SCORE,
    ATTR_SOLAR_SCORE,
    ATTR_TEMPERATURE_SCORE,
    ATTR_TOMORROW_INDEX,
    ATTR_VPD_KPA,
    ATTR_WIND_SCORE,
    DOMAIN,
)
from .coordinator import LaundryAdvisorCoordinator, LaundryAdvisorData


def _index_extra_attributes(data: LaundryAdvisorData) -> dict[str, Any]:
    """Build rich dashboard attributes for the main Laundry Index sensor."""
    attrs: dict[str, Any] = {
        ATTR_TOMORROW_INDEX: data.tomorrow_index,
        ATTR_LOAD_TYPE: data.load_type,
        ATTR_ESTIMATED_DRYING_TIME: data.estimated_drying_time,
    }
    if data.breakdown is not None:
        attrs.update(
            {
                ATTR_RAIN_SCORE: data.breakdown.rain_score,
                ATTR_HUMIDITY_SCORE: data.breakdown.humidity_score,
                ATTR_TEMPERATURE_SCORE: data.breakdown.temperature_score,
                ATTR_WIND_SCORE: data.breakdown.wind_score,
                ATTR_SOLAR_SCORE: data.breakdown.solar_score,
                ATTR_VPD_KPA: data.breakdown.vpd_kpa,
                ATTR_HOURLY_SCORES: list(data.breakdown.hourly_scores),
            }
        )
    return attrs


@dataclass(frozen=True, kw_only=True)
class LaundryAdvisorSensorEntityDescription(SensorEntityDescription):
    """Describe a Laundry Advisor sensor."""

    value_fn: Callable[[LaundryAdvisorData], Any]
    attr_fn: Callable[[LaundryAdvisorData], dict[str, Any] | None] | None = None


SENSOR_DESCRIPTIONS: tuple[LaundryAdvisorSensorEntityDescription, ...] = (
    LaundryAdvisorSensorEntityDescription(
        key="laundry_index",
        translation_key="laundry_index",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        icon="mdi:washing-machine",
        value_fn=lambda data: data.index,
        attr_fn=_index_extra_attributes,
    ),
    LaundryAdvisorSensorEntityDescription(
        key="laundry_status",
        translation_key="laundry_status",
        icon="mdi:tshirt-crew",
        value_fn=lambda data: data.status,
    ),
    LaundryAdvisorSensorEntityDescription(
        key="laundry_recommendation",
        translation_key="laundry_recommendation",
        icon="mdi:message-text-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.recommendation,
    ),
    LaundryAdvisorSensorEntityDescription(
        key="laundry_drying_window",
        translation_key="laundry_drying_window",
        icon="mdi:weather-windy",
        value_fn=lambda data: data.drying_window,
    ),
    LaundryAdvisorSensorEntityDescription(
        key="laundry_estimated_drying_time",
        translation_key="laundry_estimated_drying_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:timer-sand",
        value_fn=lambda data: data.estimated_drying_time,
        attr_fn=lambda data: {ATTR_LOAD_TYPE: data.load_type},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LaundryAdvisorConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Laundry Advisor sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        LaundryAdvisorSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class LaundryAdvisorSensor(
    CoordinatorEntity[LaundryAdvisorCoordinator],
    SensorEntity,
):
    """Representation of a Laundry Advisor sensor."""

    entity_description: LaundryAdvisorSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LaundryAdvisorCoordinator,
        entry: LaundryAdvisorConfigEntry,
        description: LaundryAdvisorSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Laundry Advisor",
            manufacturer="Laundry Advisor",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes if defined by the entity description."""
        if self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)
