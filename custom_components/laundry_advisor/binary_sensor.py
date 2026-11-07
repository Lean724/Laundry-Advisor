"""Binary sensor platform for Laundry Advisor."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LaundryAdvisorConfigEntry
from .const import DOMAIN
from .coordinator import LaundryAdvisorCoordinator

GOOD_DAY_DESCRIPTION = BinarySensorEntityDescription(
    key="laundry_good_day",
    translation_key="laundry_good_day",
    icon="mdi:white-balance-sunny",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LaundryAdvisorConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Laundry Advisor binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities([LaundryGoodDayBinarySensor(coordinator, entry)])


class LaundryGoodDayBinarySensor(
    CoordinatorEntity[LaundryAdvisorCoordinator],
    BinarySensorEntity,
):
    """Binary sensor indicating whether today is good for laundry."""

    entity_description = GOOD_DAY_DESCRIPTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LaundryAdvisorCoordinator,
        entry: LaundryAdvisorConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_laundry_good_day"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Laundry Advisor",
            manufacturer="Laundry Advisor",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def is_on(self) -> bool:
        """Return true when laundry is recommended today."""
        return self.coordinator.data.good_day
