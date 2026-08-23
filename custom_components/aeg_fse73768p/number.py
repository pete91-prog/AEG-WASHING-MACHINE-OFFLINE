"""Delay start on the real dishwasher."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance import ApplianceError
from .const import DOMAIN
from .coordinator import AEGCoordinator
from .entity import AEGEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AEGCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AEGDelayStart(coordinator)])


class AEGDelayStart(AEGEntity, NumberEntity):
    _attr_translation_key = "delay_start"
    _attr_icon = "mdi:clock-plus"
    _attr_native_min_value = 0
    _attr_native_max_value = 24
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "h"
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: AEGCoordinator) -> None:
        super().__init__(coordinator, "delay_start")

    @property
    def native_value(self) -> float:
        return self.appliance.delay_hours

    async def async_set_native_value(self, value: float) -> None:
        try:
            self.appliance.set_delay_hours(int(value))
        except ApplianceError as err:
            raise ServiceValidationError(str(err)) from err
        await self.coordinator.async_sync_selections()
