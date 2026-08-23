"""Config flow — connect the real FSE73768P via Electrolux."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import slugify

try:
    from homeassistant.config_entries import ConfigFlowResult
except ImportError:  # Home Assistant < 2024.4
    from homeassistant.data_entry_flow import FlowResult as ConfigFlowResult

from .appliance import ApplianceError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_API_KEY,
    CONF_APPLIANCE_ID,
    CONF_REFRESH_TOKEN,
    DEFAULT_NAME,
    DOMAIN,
)
from .electrolux import ElectroluxAPI, ElectroluxAuthError, list_dishwashers


class AEGFSE73768PConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add the real dishwasher using Electrolux developer credentials."""

    VERSION = 2

    def __init__(self) -> None:
        self._name = DEFAULT_NAME
        self._api_key = ""
        self._access = ""
        self._refresh = ""
        self._appliances: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._name = user_input[CONF_NAME].strip() or DEFAULT_NAME
            self._api_key = user_input[CONF_API_KEY].strip()
            self._access = user_input[CONF_ACCESS_TOKEN].strip()
            self._refresh = user_input[CONF_REFRESH_TOKEN].strip()
            try:
                client = ElectroluxAPI(
                    async_get_clientsession(self.hass),
                    self._api_key,
                    self._access,
                    self._refresh,
                )
                raw = await client.get_appliances()
                self._appliances = list_dishwashers(raw)
                self._access = client.access_token
                self._refresh = client.refresh_token
            except ElectroluxAuthError:
                errors["base"] = "invalid_auth"
            except ApplianceError:
                errors["base"] = "cannot_connect"
            else:
                if not self._appliances:
                    errors["base"] = "no_appliances"
                elif len(self._appliances) == 1:
                    return await self._async_create(self._appliances[0])
                else:
                    return await self.async_step_pick()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=self._name): str,
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_ACCESS_TOKEN): str,
                    vol.Required(CONF_REFRESH_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            chosen = next(
                item for item in self._appliances if item["id"] == user_input[CONF_APPLIANCE_ID]
            )
            return await self._async_create(chosen)

        choices = {
            item["id"]: f"{item['name']} ({item['model'] or item['type']})"
            for item in self._appliances
        }
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema({vol.Required(CONF_APPLIANCE_ID): vol.In(choices)}),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Replace Electrolux tokens on an existing entry."""
        return await self.async_step_user(user_input)

    async def _async_create(self, appliance: dict[str, str]) -> ConfigFlowResult:
        await self.async_set_unique_id(f"{DOMAIN}_{slugify(appliance['id'])}")
        title = self._name if self._name != DEFAULT_NAME else appliance["name"]
        data = {
            CONF_NAME: title,
            CONF_API_KEY: self._api_key,
            CONF_ACCESS_TOKEN: self._access,
            CONF_REFRESH_TOKEN: self._refresh,
            CONF_APPLIANCE_ID: appliance["id"],
        }
        if self.source == "reconfigure":
            return self.async_update_reload_and_abort(
                self._reconfigure_entry(),
                title=title,
                data=data,
            )
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=title, data=data)

    def _reconfigure_entry(self):
        getter = getattr(self, "_get_reconfigure_entry", None)
        if getter:
            return getter()
        return self.hass.config_entries.async_get_entry(self.context["entry_id"])
