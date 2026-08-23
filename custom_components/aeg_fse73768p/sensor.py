"""Sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfEnergy, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .appliance import Appliance
from .const import ATTRIBUTION, DOMAIN
from .coordinator import AEGCoordinator
from .entity import AEGEntity
from .programs import PHASE_LABELS, PROGRAMS


@dataclass(frozen=True, kw_only=True)
class AEGSensorDescription(SensorEntityDescription):
    value_fn: Callable[[Appliance], StateType]
    attrs_fn: Callable[[Appliance], dict] | None = None


def _remaining_minutes(appliance: Appliance) -> int:
    return int(round(appliance.remaining_seconds / 60))


SENSORS: tuple[AEGSensorDescription, ...] = (
    AEGSensorDescription(
        key="state",
        translation_key="state",
        icon="mdi:dishwasher",
        device_class=SensorDeviceClass.ENUM,
        options=["off", "idle", "delayed", "running", "paused", "airdry", "complete", "error"],
        value_fn=lambda a: a.state,
        attrs_fn=lambda a: {**a.snapshot(), "attribution": ATTRIBUTION},
    ),
    AEGSensorDescription(
        key="program",
        translation_key="program",
        icon="mdi:dishwasher",
        device_class=SensorDeviceClass.ENUM,
        options=list(PROGRAMS),
        value_fn=lambda a: a.program_id,
    ),
    AEGSensorDescription(
        key="cycle_phase",
        translation_key="cycle_phase",
        icon="mdi:progress-clock",
        device_class=SensorDeviceClass.ENUM,
        options=list(PHASE_LABELS),
        value_fn=lambda a: a.phase,
    ),
    AEGSensorDescription(
        key="time_remaining",
        translation_key="time_remaining",
        icon="mdi:timer-sand",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_display_precision=0,
        value_fn=_remaining_minutes,
    ),
    AEGSensorDescription(
        key="cycle_progress",
        translation_key="cycle_progress",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda a: a.progress,
    ),
    AEGSensorDescription(
        key="wash_temperature",
        translation_key="wash_temperature",
        icon="mdi:thermometer-water",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        value_fn=lambda a: a.cycle.wash_temp,
    ),
    AEGSensorDescription(
        key="current_temperature",
        translation_key="current_temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda a: a.current_temperature(),
    ),
    AEGSensorDescription(
        key="ecometer",
        translation_key="ecometer",
        icon="mdi:leaf",
        native_unit_of_measurement="bars",
        value_fn=lambda a: a.cycle.ecometer,
    ),
    AEGSensorDescription(
        key="beam_on_floor",
        translation_key="beam_on_floor",
        icon="mdi:spotlight-beam",
        device_class=SensorDeviceClass.ENUM,
        options=["off", "red", "green", "flash"],
        value_fn=lambda a: a.beam,
    ),
    AEGSensorDescription(
        key="estimated_energy",
        translation_key="estimated_energy",
        icon="mdi:flash",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=lambda a: a.energy_used_kwh(),
    ),
    AEGSensorDescription(
        key="estimated_water",
        translation_key="estimated_water",
        icon="mdi:water",
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=1,
        value_fn=lambda a: a.water_used_l(),
    ),
    AEGSensorDescription(
        key="cycle_count",
        translation_key="cycle_count",
        icon="mdi:counter",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda a: a.cycle_count,
    ),
    AEGSensorDescription(
        key="noise",
        translation_key="noise",
        icon="mdi:volume-medium",
        native_unit_of_measurement="dB",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda a: a.cycle.noise_db,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AEGCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AEGSensor(coordinator, description) for description in SENSORS)


class AEGSensor(AEGEntity, SensorEntity):
    """Dishwasher sensor."""

    entity_description: AEGSensorDescription

    def __init__(self, coordinator: AEGCoordinator, description: AEGSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.appliance)

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.entity_description.attrs_fn:
            return self.entity_description.attrs_fn(self.appliance)
        return None
