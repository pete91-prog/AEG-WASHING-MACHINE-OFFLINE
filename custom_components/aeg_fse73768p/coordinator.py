"""Data update coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .appliance import (
    STATE_AIRDRY,
    STATE_DELAYED,
    STATE_IDLE,
    STATE_OFF,
    STATE_PAUSED,
    STATE_RUNNING,
    Appliance,
)
from .cloud_state import apply_cloud_state
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_API_KEY,
    CONF_APPLIANCE_ID,
    CONF_REFRESH_TOKEN,
)
from .electrolux import ElectroluxAPI

_LOGGER = logging.getLogger(__name__)

ACTIVE_STATES = {STATE_RUNNING, STATE_DELAYED, STATE_AIRDRY, STATE_PAUSED}


class AEGCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the real dishwasher when cloud credentials exist."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        appliance: Appliance,
        store: Store,
        client: ElectroluxAPI | None = None,
    ) -> None:
        interval = timedelta(seconds=20 if client else 15)
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=interval,
            config_entry=entry,
        )
        self.entry = entry
        self.appliance = appliance
        self.client = client
        self.appliance_id = entry.data.get(CONF_APPLIANCE_ID)
        self._store = store
        self._dirty = False

    @property
    def is_cloud(self) -> bool:
        return self.client is not None and bool(self.appliance_id)

    async def async_setup_cloud(self) -> None:
        if not self.is_cloud:
            return
        assert self.client and self.appliance_id
        await self.client.load_program_map(self.appliance_id)
        self.appliance.cloud = True

    async def _async_update_data(self) -> dict[str, Any]:
        if self.is_cloud:
            assert self.client and self.appliance_id
            payload = await self.client.get_state(self.appliance_id)
            apply_cloud_state(self.appliance, payload)
            return self.appliance.snapshot()

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
        if self.is_cloud:
            await self.async_request_refresh()
            return
        self.mark_dirty()
        if self.appliance.state in ACTIVE_STATES:
            self.update_interval = timedelta(seconds=1)
        else:
            self.update_interval = timedelta(seconds=15)
        self.async_set_updated_data(self.appliance.snapshot())
        await self.async_save()

    async def async_set_program(self, program_id: str) -> None:
        self.appliance.set_program(program_id)
        if self.is_cloud:
            assert self.client and self.appliance_id
            await self.client.set_program(
                self.appliance_id, program_id, self.appliance.extras
            )
        await self.async_push()

    async def async_sync_selections(self) -> None:
        """Push extras / delay to the machine when it is idle."""
        if self.is_cloud and self.appliance.state in {STATE_IDLE, STATE_OFF}:
            assert self.client and self.appliance_id
            await self.client.set_program(
                self.appliance_id,
                self.appliance.program_id,
                self.appliance.extras,
                start_in=self.appliance.delay_hours * 3600,
            )
        await self.async_push()

    async def async_start(self, program_id: str | None = None) -> None:
        if self.is_cloud:
            assert self.client and self.appliance_id
            if self.appliance.state == STATE_PAUSED:
                await self.client.resume(self.appliance_id)
                self.appliance.state = STATE_RUNNING
                self.appliance.phase = "main_wash"
                self.appliance._touch()
                await self.async_request_refresh()
                return
            if self.appliance.state in {STATE_RUNNING, STATE_AIRDRY, STATE_DELAYED}:
                return
            if program_id:
                self.appliance.set_program(program_id)
            await self.client.set_program(
                self.appliance_id,
                self.appliance.program_id,
                self.appliance.extras,
                start_in=self.appliance.delay_hours * 3600,
            )
            await self.client.start(self.appliance_id)
            if self.appliance.delay_hours:
                self.appliance.state = STATE_DELAYED
                self.appliance.phase = "delay"
            else:
                self.appliance.state = STATE_RUNNING
                self.appliance.phase = "main_wash"
            self.appliance._touch()
            await self.async_request_refresh()
            return
        self.appliance.start(program_id)
        await self.async_push()

    async def async_pause(self) -> None:
        if self.is_cloud:
            assert self.client and self.appliance_id
            await self.client.pause(self.appliance_id)
            self.appliance.state = STATE_PAUSED
            self.appliance.phase = "paused"
            self.appliance._touch()
            await self.async_request_refresh()
            return
        self.appliance.pause()
        await self.async_push()

    async def async_resume(self) -> None:
        if self.is_cloud:
            assert self.client and self.appliance_id
            await self.client.resume(self.appliance_id)
            self.appliance.state = STATE_RUNNING
            self.appliance.phase = "main_wash"
            self.appliance._touch()
            await self.async_request_refresh()
            return
        self.appliance.resume()
        await self.async_push()

    async def async_cancel(self) -> None:
        if self.is_cloud:
            assert self.client and self.appliance_id
            await self.client.stop(self.appliance_id)
            self.appliance.cancel()
            await self.async_request_refresh()
            return
        self.appliance.cancel()
        await self.async_push()


def create_cloud_client(hass: HomeAssistant, entry: ConfigEntry) -> ElectroluxAPI | None:
    api_key = entry.data.get(CONF_API_KEY)
    access = entry.data.get(CONF_ACCESS_TOKEN)
    refresh = entry.data.get(CONF_REFRESH_TOKEN)
    if not (api_key and access and refresh):
        return None

    @callback
    def _store_tokens(access_token: str, refresh_token: str) -> None:
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_ACCESS_TOKEN: access_token, CONF_REFRESH_TOKEN: refresh_token},
        )

    return ElectroluxAPI(
        async_get_clientsession(hass),
        api_key,
        access,
        refresh,
        on_tokens=_store_tokens,
    )
