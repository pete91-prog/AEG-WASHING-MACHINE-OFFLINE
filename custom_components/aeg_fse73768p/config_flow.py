"""Config flow for the offline AEG FSE73768P."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_NAME
from homeassistant.util import slugify

try:
    from homeassistant.config_entries import ConfigFlowResult
except ImportError:  # Home Assistant < 2024.4
    from homeassistant.data_entry_flow import FlowResult as ConfigFlowResult

from .const import DEFAULT_NAME, DOMAIN


class AEGFSE73768PConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a fully offline dishwasher — no account, no cloud."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            name = user_input[CONF_NAME].strip() or DEFAULT_NAME
            await self.async_set_unique_id(f"{DOMAIN}_{slugify(name)}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=name, data={CONF_NAME: name})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                }
            ),
        )
