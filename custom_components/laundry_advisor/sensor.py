"""Sensor platform for Laundry Advisor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LaundryAdvisorConfigEntry
from .const import DOMAIN
from .coordinator import LaundryAdvisorCoordinator, LaundryAdvisorData


@dataclass(frozen=True, kw_only=True)
class LaundryAdvisorSensorEntityDescription(SensorEntityDescription):
    """Describe a Laundry Advisor sensor."""

    value_fn: Callable[[LaundryAdvisorData], Any]


SENSOR_DESCRIPTIONS: tuple[LaundryAdvisorSensorEntityDescription, ...] = (
    LaundryAdvisorSensorEntityDescription(
        key="laundry_index",
        translation_key="laundry_index",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        icon="mdi:washing-machine",
        value_fn=lambda data: data.index,
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
