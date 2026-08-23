"""Data update coordinator — live Electrolux dishwasher only."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
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


class AEGCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the real FSE73768P through the Electrolux API."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        appliance: Appliance,
        client: ElectroluxAPI,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=timedelta(seconds=20),
            config_entry=entry,
        )
        self.entry = entry
        self.appliance = appliance
        self.client = client
        self.appliance_id = str(entry.data[CONF_APPLIANCE_ID])

    async def async_setup(self) -> None:
        await self.client.load_program_map(self.appliance_id)

    async def _async_update_data(self) -> dict[str, Any]:
        payload = await self.client.get_state(self.appliance_id)
        apply_cloud_state(self.appliance, payload)
        return self.appliance.snapshot()

    async def async_push(self) -> None:
        await self.async_request_refresh()

    async def async_set_program(self, program_id: str) -> None:
        self.appliance.set_program(program_id)
        await self.client.set_program(
            self.appliance_id, program_id, self.appliance.extras
        )
        await self.async_push()

    async def async_sync_selections(self) -> None:
        """Push extras / delay to the machine when it is idle."""
        if self.appliance.state in {STATE_IDLE, STATE_OFF}:
            await self.client.set_program(
                self.appliance_id,
                self.appliance.program_id,
                self.appliance.extras,
                start_in=self.appliance.delay_hours * 3600,
            )
        await self.async_push()

    async def async_start(self, program_id: str | None = None) -> None:
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

    async def async_pause(self) -> None:
        await self.client.pause(self.appliance_id)
        self.appliance.state = STATE_PAUSED
        self.appliance.phase = "paused"
        self.appliance._touch()
        await self.async_request_refresh()

    async def async_resume(self) -> None:
        await self.client.resume(self.appliance_id)
        self.appliance.state = STATE_RUNNING
        self.appliance.phase = "main_wash"
        self.appliance._touch()
        await self.async_request_refresh()

    async def async_cancel(self) -> None:
        await self.client.stop(self.appliance_id)
        self.appliance.cancel()
        await self.async_request_refresh()


def create_cloud_client(hass: HomeAssistant, entry: ConfigEntry) -> ElectroluxAPI:
    api_key = entry.data.get(CONF_API_KEY)
    access = entry.data.get(CONF_ACCESS_TOKEN)
    refresh = entry.data.get(CONF_REFRESH_TOKEN)
    appliance_id = entry.data.get(CONF_APPLIANCE_ID)
    if not (api_key and access and refresh and appliance_id):
        raise ConfigEntryAuthFailed(
            "Electrolux API key, tokens, and the dishwasher id are required"
        )

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
