"""Programme select."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance import ApplianceError
from .const import DOMAIN
from .coordinator import AEGCoordinator
from .entity import AEGEntity
from .programs import PROGRAM_ORDER


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AEGCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AEGProgramSelect(coordinator)])


class AEGProgramSelect(AEGEntity, SelectEntity):
    _attr_translation_key = "program"
    _attr_icon = "mdi:dishwasher"
    _attr_options = list(PROGRAM_ORDER)

    def __init__(self, coordinator: AEGCoordinator) -> None:
        super().__init__(coordinator, "program_select")

    @property
    def current_option(self) -> str:
        return self.appliance.program_id

    async def async_select_option(self, option: str) -> None:
        try:
            await self.coordinator.async_set_program(option)
        except ApplianceError as err:
            raise ServiceValidationError(str(err)) from err
