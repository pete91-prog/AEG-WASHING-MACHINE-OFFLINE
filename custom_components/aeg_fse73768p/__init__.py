"""AEG FSE73768P offline Home Assistant integration."""

from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .appliance import Appliance, ApplianceError
from .const import DEFAULT_NAME, DOMAIN, PLATFORMS, STORAGE_VERSION
from .coordinator import AEGCoordinator
from .frontend import JSModuleRegistration
from .programs import PROGRAMS

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_START = "start_program"
SERVICE_PAUSE = "pause"
SERVICE_RESUME = "resume"
SERVICE_CANCEL = "cancel"
SERVICE_SET_DOOR = "set_door"

START_SCHEMA = vol.Schema(
    {
        vol.Optional("device_id"): cv.string,
        vol.Optional("program"): vol.In(list(PROGRAMS)),
        vol.Optional("extra_power"): cv.boolean,
        vol.Optional("glass_care"): cv.boolean,
        vol.Optional("extra_silent"): cv.boolean,
        vol.Optional("delay_hours"): vol.All(vol.Coerce(int), vol.Range(min=0, max=24)),
    }
)

DEVICE_SCHEMA = vol.Schema({vol.Optional("device_id"): cv.string})
DOOR_SCHEMA = vol.Schema(
    {
        vol.Optional("device_id"): cv.string,
        vol.Required("open"): cv.boolean,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration (config-entry only)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one offline dishwasher."""
    hass.data.setdefault(DOMAIN, {})
    store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
    stored = await store.async_load() or {}
    appliance = Appliance(name=entry.data.get(CONF_NAME, DEFAULT_NAME))
    appliance.restore(stored)

    coordinator = AEGCoordinator(hass, entry, appliance, store)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await JSModuleRegistration(hass).async_register()
    _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator: AEGCoordinator | None = hass.data[DOMAIN].pop(entry.entry_id, None)
    if coordinator:
        await coordinator.async_save()
    return unload_ok


def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_START):
        return

    async def _start(call: ServiceCall) -> None:
        coordinator = _resolve(hass, call)
        try:
            if "delay_hours" in call.data:
                coordinator.appliance.set_delay_hours(call.data["delay_hours"])
            if "extra_power" in call.data:
                coordinator.appliance.set_extra("extra_power", call.data["extra_power"])
            if "glass_care" in call.data:
                coordinator.appliance.set_extra("glass_care", call.data["glass_care"])
            if "extra_silent" in call.data:
                coordinator.appliance.set_extra("extra_silent", call.data["extra_silent"])
            coordinator.appliance.start(call.data.get("program"))
        except ApplianceError as err:
            raise ServiceValidationError(str(err)) from err
        await coordinator.async_push()

    async def _pause(call: ServiceCall) -> None:
        coordinator = _resolve(hass, call)
        coordinator.appliance.pause()
        await coordinator.async_push()

    async def _resume(call: ServiceCall) -> None:
        coordinator = _resolve(hass, call)
        try:
            coordinator.appliance.resume()
        except ApplianceError as err:
            raise ServiceValidationError(str(err)) from err
        await coordinator.async_push()

    async def _cancel(call: ServiceCall) -> None:
        coordinator = _resolve(hass, call)
        coordinator.appliance.cancel()
        await coordinator.async_push()

    async def _set_door(call: ServiceCall) -> None:
        coordinator = _resolve(hass, call)
        coordinator.appliance.set_door(call.data["open"])
        await coordinator.async_push()

    hass.services.async_register(DOMAIN, SERVICE_START, _start, schema=START_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_PAUSE, _pause, schema=DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_RESUME, _resume, schema=DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CANCEL, _cancel, schema=DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_DOOR, _set_door, schema=DOOR_SCHEMA)


def _resolve(hass: HomeAssistant, call: ServiceCall) -> AEGCoordinator:
    entries: dict[str, AEGCoordinator] = hass.data.get(DOMAIN, {})
    if not entries:
        raise HomeAssistantError("No AEG FSE73768P has been added")
    device_id = call.data.get("device_id")
    if not device_id:
        if len(entries) == 1:
            return next(iter(entries.values()))
        raise ServiceValidationError("device_id is required when several dishwashers exist")

    registry = dr.async_get(hass)
    device = registry.async_get(device_id)
    if not device:
        raise ServiceValidationError("Unknown device")
    for ident in device.identifiers:
        if ident[0] == DOMAIN and ident[1] in entries:
            return entries[ident[1]]
    raise ServiceValidationError("Device is not an AEG FSE73768P")
