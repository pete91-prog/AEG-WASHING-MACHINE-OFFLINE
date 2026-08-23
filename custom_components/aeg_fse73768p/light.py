"""Interior light."""

from __future__ import annotations

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AEGCoordinator
from .entity import AEGEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AEGCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AEGInteriorLight(coordinator)])


class AEGInteriorLight(AEGEntity, LightEntity):
    _attr_translation_key = "interior_light"
    _attr_icon = "mdi:lightbulb-on"
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, coordinator: AEGCoordinator) -> None:
        super().__init__(coordinator, "interior_light")

    @property
    def is_on(self) -> bool:
        return self.appliance.interior_light

    @property
    def available(self) -> bool:
        return super().available and self.appliance.powered

    async def async_turn_on(self, **kwargs) -> None:
        if not self.appliance.door_open:
            raise ServiceValidationError("Open the door to use the interior light")
        self.appliance.interior_light_on = True
        self.appliance._touch()
        await self.coordinator.async_push()

    async def async_turn_off(self, **kwargs) -> None:
        self.appliance.interior_light_on = False
        self.appliance._touch()
        await self.coordinator.async_push()
