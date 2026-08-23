"""Switches for power, extras, door and settings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance import Appliance, ApplianceError
from .const import DOMAIN
from .coordinator import AEGCoordinator
from .entity import AEGEntity
from .programs import EXTRA_POWER, EXTRA_SILENT, GLASS_CARE


@dataclass(frozen=True, kw_only=True)
class AEGSwitchDescription(SwitchEntityDescription):
    is_on_fn: Callable[[Appliance], bool]
    turn_on_fn: Callable[[Appliance], None]
    turn_off_fn: Callable[[Appliance], None]
    available_fn: Callable[[Appliance], bool] = lambda _a: True


def _set_extra(extra: str, enabled: bool) -> Callable[[Appliance], None]:
    def _apply(appliance: Appliance) -> None:
        appliance.set_extra(extra, enabled)

    return _apply


SWITCHES: tuple[AEGSwitchDescription, ...] = (
    AEGSwitchDescription(
        key="power",
        translation_key="power",
        icon="mdi:power",
        is_on_fn=lambda a: a.powered,
        turn_on_fn=lambda a: a.power_on(),
        turn_off_fn=lambda a: a.power_off(),
    ),
    AEGSwitchDescription(
        key="door",
        translation_key="door_switch",
        icon="mdi:door",
        is_on_fn=lambda a: a.door_open,
        turn_on_fn=lambda a: a.set_door(True),
        turn_off_fn=lambda a: a.set_door(False),
    ),
    AEGSwitchDescription(
        key="extra_power",
        translation_key="extra_power",
        icon="mdi:fire",
        is_on_fn=lambda a: EXTRA_POWER in a.extras,
        turn_on_fn=_set_extra(EXTRA_POWER, True),
        turn_off_fn=_set_extra(EXTRA_POWER, False),
        available_fn=lambda a: EXTRA_POWER in a.program.extras,
    ),
    AEGSwitchDescription(
        key="glass_care",
        translation_key="glass_care",
        icon="mdi:glass-fragile",
        is_on_fn=lambda a: GLASS_CARE in a.extras,
        turn_on_fn=_set_extra(GLASS_CARE, True),
        turn_off_fn=_set_extra(GLASS_CARE, False),
        available_fn=lambda a: GLASS_CARE in a.program.extras,
    ),
    AEGSwitchDescription(
        key="extra_silent",
        translation_key="extra_silent",
        icon="mdi:volume-off",
        is_on_fn=lambda a: EXTRA_SILENT in a.extras,
        turn_on_fn=_set_extra(EXTRA_SILENT, True),
        turn_off_fn=_set_extra(EXTRA_SILENT, False),
        available_fn=lambda a: EXTRA_SILENT in a.program.extras,
    ),
    AEGSwitchDescription(
        key="airdry",
        translation_key="airdry",
        icon="mdi:door-open",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda a: a.airdry_enabled,
        turn_on_fn=lambda a: setattr(a, "airdry_enabled", True),
        turn_off_fn=lambda a: setattr(a, "airdry_enabled", False),
    ),
    AEGSwitchDescription(
        key="end_sound",
        translation_key="end_sound",
        icon="mdi:volume-high",
        entity_category=EntityCategory.CONFIG,
        is_on_fn=lambda a: a.end_sound,
        turn_on_fn=lambda a: setattr(a, "end_sound", True),
        turn_off_fn=lambda a: setattr(a, "end_sound", False),
    ),
    AEGSwitchDescription(
        key="comfort_lift",
        translation_key="comfort_lift",
        icon="mdi:arrow-up-bold-box",
        is_on_fn=lambda a: a.comfort_lift and a.door_open,
        turn_on_fn=lambda a: setattr(a, "comfort_lift", True) if a.door_open else None,
        turn_off_fn=lambda a: setattr(a, "comfort_lift", False),
        available_fn=lambda a: a.door_open,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AEGCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AEGSwitch(coordinator, description) for description in SWITCHES)


class AEGSwitch(AEGEntity, SwitchEntity):
    entity_description: AEGSwitchDescription

    def __init__(self, coordinator: AEGCoordinator, description: AEGSwitchDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.is_on_fn(self.appliance)

    @property
    def available(self) -> bool:
        return super().available and self.entity_description.available_fn(self.appliance)

    async def async_turn_on(self, **kwargs) -> None:
        try:
            self.entity_description.turn_on_fn(self.appliance)
        except ApplianceError as err:
            raise ServiceValidationError(str(err)) from err
        self.appliance._touch()
        await self.coordinator.async_push()

    async def async_turn_off(self, **kwargs) -> None:
        try:
            self.entity_description.turn_off_fn(self.appliance)
        except ApplianceError as err:
            raise ServiceValidationError(str(err)) from err
        self.appliance._touch()
        await self.coordinator.async_push()
