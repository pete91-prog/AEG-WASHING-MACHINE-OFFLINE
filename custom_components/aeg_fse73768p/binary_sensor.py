"""Binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance import STATE_RUNNING, STATE_AIRDRY, Appliance
from .const import DOMAIN
from .coordinator import AEGCoordinator
from .entity import AEGEntity


@dataclass(frozen=True, kw_only=True)
class AEGBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[Appliance], bool]


SENSORS: tuple[AEGBinaryDescription, ...] = (
    AEGBinaryDescription(
        key="running",
        translation_key="running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda a: a.state in {STATE_RUNNING, STATE_AIRDRY},
    ),
    AEGBinaryDescription(
        key="door_open",
        translation_key="door",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=lambda a: a.door_open,
    ),
    AEGBinaryDescription(
        key="salt",
        translation_key="salt",
        icon="mdi:shaker-outline",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda a: not a.salt_ok,
    ),
    AEGBinaryDescription(
        key="rinse_aid",
        translation_key="rinse_aid",
        icon="mdi:water-alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda a: not a.rinse_aid_ok,
    ),
    AEGBinaryDescription(
        key="machine_care",
        translation_key="machine_care",
        icon="mdi:wrench",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda a: a.machine_care_needed,
    ),
    AEGBinaryDescription(
        key="connectivity",
        translation_key="connectivity",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda a: a.powered,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AEGCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AEGBinarySensor(coordinator, description) for description in SENSORS)


class AEGBinarySensor(AEGEntity, BinarySensorEntity):
    entity_description: AEGBinaryDescription

    def __init__(self, coordinator: AEGCoordinator, description: AEGBinaryDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.appliance)
