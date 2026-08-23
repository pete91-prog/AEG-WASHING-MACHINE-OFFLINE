"""Diagnostics."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_API_KEY,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)
from .coordinator import AEGCoordinator

_REDACT = {CONF_API_KEY, CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN}


def _redact(data: dict[str, Any]) -> dict[str, Any]:
    return {key: "**REDACTED**" if key in _REDACT else value for key, value in data.items()}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: AEGCoordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": {"title": entry.title, "data": _redact(dict(entry.data))},
        "cloud": coordinator.is_cloud,
        "appliance": coordinator.appliance.snapshot(),
    }
