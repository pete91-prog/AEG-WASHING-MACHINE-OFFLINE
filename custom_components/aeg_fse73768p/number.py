"""Numeric settings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance import Appliance, ApplianceError
from .const import DOMAIN
from .coordinator import AEGCoordinator
from .entity import AEGEntity


@dataclass(frozen=True, kw_only=True)
class AEGNumberDescription(NumberEntityDescription):
    value_fn: Callable[[Appliance], float]
    set_fn: Callable[[Appliance, float], None]


NUMBERS: tuple[AEGNumberDescription, ...] = (
    AEGNumberDescription(
        key="delay_start",
        translation_key="delay_start",
        icon="mdi:clock-plus",
        native_min_value=0,
        native_max_value=24,
        native_step=1,
        native_unit_of_measurement="h",
        mode=NumberMode.SLIDER,
        value_fn=lambda a: a.delay_hours,
        set_fn=lambda a, v: a.set_delay_hours(int(v)),
    ),
    AEGNumberDescription(
        key="water_softener",
        translation_key="water_softener",
        icon="mdi:water-opacity",
        entity_category=EntityCategory.CONFIG,
        native_min_value=1,
        native_max_value=10,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda a: a.water_softener,
        set_fn=lambda a, v: setattr(a, "water_softener", int(v)),
    ),
    AEGNumberDescription(
        key="rinse_aid_dosage",
        translation_key="rinse_aid_dosage",
        icon="mdi:cup-water",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=6,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda a: a.rinse_aid_level,
        set_fn=lambda a, v: setattr(a, "rinse_aid_level", int(v)),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AEGCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AEGNumber(coordinator, description) for description in NUMBERS)


class AEGNumber(AEGEntity, NumberEntity):
    entity_description: AEGNumberDescription

    def __init__(self, coordinator: AEGCoordinator, description: AEGNumberDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float:
        return self.entity_description.value_fn(self.appliance)

    async def async_set_native_value(self, value: float) -> None:
        try:
            self.entity_description.set_fn(self.appliance, value)
        except ApplianceError as err:
            raise ServiceValidationError(str(err)) from err
        self.appliance._touch()
        if self._key == "delay_start":
            await self.coordinator.async_sync_selections()
            return
        await self.coordinator.async_push()
