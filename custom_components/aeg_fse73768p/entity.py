"""Shared entity base."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, MODEL_ID
from .coordinator import AEGCoordinator


class AEGEntity(CoordinatorEntity[AEGCoordinator]):
    """Base entity for the FSE73768P."""

    _attr_has_entity_name = True
    _attr_attribution = "Offline AEG FSE73768P — no cloud"

    def __init__(self, coordinator: AEGCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            model_id=MODEL_ID,
            name=coordinator.appliance.name,
            sw_version="1.0.0",
            hw_version="7000 ComfortLift",
            serial_number=MODEL_ID,
        )

    @property
    def appliance(self):
        return self.coordinator.appliance
