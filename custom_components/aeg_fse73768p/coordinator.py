"""Data update coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .appliance import STATE_DELAYED, STATE_RUNNING, STATE_AIRDRY, STATE_PAUSED, Appliance

_LOGGER = logging.getLogger(__name__)

ACTIVE_STATES = {STATE_RUNNING, STATE_DELAYED, STATE_AIRDRY, STATE_PAUSED}


class AEGCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Ticks the local dishwasher and persists settings."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        appliance: Appliance,
        store: Store,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=timedelta(seconds=1),
            config_entry=entry,
        )
        self.entry = entry
        self.appliance = appliance
        self._store = store
        self._dirty = False

    async def _async_update_data(self) -> dict[str, Any]:
        changed = await self.hass.async_add_executor_job(self.appliance.tick)
        if changed:
            self._dirty = True
        if self.appliance.state in ACTIVE_STATES:
            self.update_interval = timedelta(seconds=1)
        else:
            self.update_interval = timedelta(seconds=15)
        if self._dirty and self.appliance.state not in ACTIVE_STATES:
            await self.async_save()
        return self.appliance.snapshot()

    async def async_save(self) -> None:
        await self._store.async_save(self.appliance.to_storage())
        self._dirty = False

    def mark_dirty(self) -> None:
        self._dirty = True

    async def async_push(self) -> None:
        """Refresh entities immediately after a user command."""
        self.mark_dirty()
        if self.appliance.state in ACTIVE_STATES:
            self.update_interval = timedelta(seconds=1)
        else:
            self.update_interval = timedelta(seconds=15)
        self.async_set_updated_data(self.appliance.snapshot())
        await self.async_save()
