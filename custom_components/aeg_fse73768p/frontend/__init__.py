"""Serve and register the Lovelace card."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from .const import CARD_FILENAME, DOMAIN, URL_BASE

_LOGGER = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent


class JSModuleRegistration:
    """Register the dishwasher card as a Lovelace module."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.lovelace = self.hass.data.get("lovelace")

    async def async_register(self) -> None:
        await self._async_register_path()
        if self.lovelace is not None and getattr(self.lovelace, "mode", None) == "storage":
            await self._async_wait_for_resources()

    async def _async_register_path(self) -> None:
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, str(FRONTEND_DIR), False)]
            )
        except RuntimeError:
            _LOGGER.debug("Static path %s already registered", URL_BASE)

    async def _async_wait_for_resources(self) -> None:
        async def _check(_now: Any) -> None:
            resources = getattr(self.lovelace, "resources", None)
            if resources is None:
                return
            if getattr(resources, "loaded", True):
                await self._async_register_modules()
            else:
                async_call_later(self.hass, 5, _check)

        await _check(0)

    async def _async_register_modules(self) -> None:
        resources = self.lovelace.resources
        url = f"{URL_BASE}/{CARD_FILENAME}"
        versioned = f"{url}?v={DOMAIN}"
        existing = [
            item
            for item in resources.async_items()
            if str(item.get("url", "")).startswith(URL_BASE)
        ]
        for item in existing:
            if item.get("url", "").split("?", 1)[0] == url:
                if item.get("url") != versioned:
                    await resources.async_update_item(
                        item["id"],
                        {"res_type": "module", "url": versioned},
                    )
                return
        await resources.async_create_item({"res_type": "module", "url": versioned})
        _LOGGER.info("Registered Lovelace card %s", url)
