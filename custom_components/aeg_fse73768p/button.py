"""Buttons — start, pause, cancel, and one-tap programmes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance import Appliance, ApplianceError
from .const import DOMAIN
from .coordinator import AEGCoordinator
from .entity import AEGEntity
from .programs import PROGRAM_ORDER, PROGRAMS


@dataclass(frozen=True, kw_only=True)
class AEGButtonDescription(ButtonEntityDescription):
    press_fn: Callable[[Appliance], None]


def _start_program(program_id: str) -> Callable[[Appliance], None]:
    def _press(appliance: Appliance) -> None:
        appliance.start(program_id)

    return _press


BUTTONS: tuple[AEGButtonDescription, ...] = (
    AEGButtonDescription(
        key="start",
        translation_key="start",
        icon="mdi:play",
        press_fn=lambda a: a.start(),
    ),
    AEGButtonDescription(
        key="pause",
        translation_key="pause",
        icon="mdi:pause",
        press_fn=lambda a: a.pause(),
    ),
    AEGButtonDescription(
        key="cancel",
        translation_key="cancel",
        icon="mdi:stop",
        press_fn=lambda a: a.cancel(),
    ),
    *(
        AEGButtonDescription(
            key=f"start_{key}",
            translation_key=f"start_{key}",
            icon="mdi:play-circle-outline",
            press_fn=_start_program(key),
        )
        for key in PROGRAM_ORDER
    ),
    AEGButtonDescription(
        key="refill_salt",
        translation_key="refill_salt",
        icon="mdi:shaker",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda a: a.refill_salt(),
    ),
    AEGButtonDescription(
        key="refill_rinse_aid",
        translation_key="refill_rinse_aid",
        icon="mdi:water-plus",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda a: a.refill_rinse_aid(),
    ),
    AEGButtonDescription(
        key="reset_machine_care",
        translation_key="reset_machine_care",
        icon="mdi:broom",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda a: a.reset_machine_care(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AEGCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AEGButton(coordinator, description) for description in BUTTONS)


class AEGButton(AEGEntity, ButtonEntity):
    entity_description: AEGButtonDescription

    def __init__(self, coordinator: AEGCoordinator, description: AEGButtonDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        if description.key.startswith("start_") and description.key != "start":
            program = PROGRAMS[description.key.removeprefix("start_")]
            self._attr_name = f"Start {program.name}"

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._key.startswith("start_") and self._key != "start":
            program = PROGRAMS[self._key.removeprefix("start_")]
            return {
                "duration_min": program.duration_min,
                "water_l": program.water_l,
                "energy_kwh": program.energy_kwh,
                "description": program.description,
            }
        return None

    async def async_press(self) -> None:
        try:
            if self._key == "start":
                await self.coordinator.async_start()
            elif self._key.startswith("start_"):
                await self.coordinator.async_start(self._key.removeprefix("start_"))
            elif self._key == "pause":
                if self.appliance.state == "paused":
                    await self.coordinator.async_resume()
                else:
                    await self.coordinator.async_pause()
            elif self._key == "cancel":
                await self.coordinator.async_cancel()
            else:
                self.entity_description.press_fn(self.appliance)
                await self.coordinator.async_push()
        except ApplianceError as err:
            raise ServiceValidationError(str(err)) from err
