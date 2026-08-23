"""Official Electrolux Group Developer API client.

Talks to api.developer.electrolux.one — the same path My AEG Kitchen uses
after you create an API key at https://developer.electrolux.one/
"""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .appliance import ApplianceError

_LOGGER = logging.getLogger(__name__)

BASE = "https://api.developer.electrolux.one/api/v1"

CONF_API_KEY = "api_key"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_APPLIANCE_ID = "appliance_id"

# Local programme key -> possible Electrolux programUID values (first match wins).
PROGRAM_UID_CANDIDATES: dict[str, tuple[str, ...]] = {
    "quick": ("QUICK30", "QUICK", "QUICK_30", "30MIN", "30MINUTES", "QUICK30MIN"),
    "1h": ("QUICK60", "1H", "60MIN", "60MINUTES", "NORMAL60", "INTENSIVE60"),
    "1h30": ("NORMAL90", "1H30", "90MIN", "90MINUTES", "1H_30MIN"),
    "2h40": ("INTENSIVE", "2H40", "160MIN", "160MINUTES", "2H_40MIN", "INTENSIVE160"),
    "eco": ("ECO", "ECO50", "ECO_50"),
    "auto_sense": ("AUTO", "AUTO_SENSE", "AUTOSENSE", "AUTO50_60"),
    "machine_care": ("MACHINE_CARE", "MACHINECARE", "MACHINECARE70"),
}

EXTRA_UIDS: dict[str, tuple[str, ...]] = {
    "extra_power": ("extraPower", "ExtraPower"),
    "glass_care": ("glassCare", "GlassCare"),
    "extra_silent": ("extraSilent", "ExtraSilent"),
}


class ElectroluxAuthError(ApplianceError):
    """Credentials or token refresh failed."""


class ElectroluxAPI:
    """Minimal async client for the official developer API."""

    def __init__(
        self,
        session: ClientSession,
        api_key: str,
        access_token: str,
        refresh_token: str,
        on_tokens: Callable[[str, str], None] | None = None,
    ) -> None:
        self._session = session
        self.api_key = api_key.strip()
        self.access_token = access_token.strip()
        self.refresh_token = refresh_token.strip()
        self._on_tokens = on_tokens
        self.program_uids: dict[str, str] = {}

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def refresh(self) -> None:
        async with self._session.post(
            f"{BASE}/token/refresh",
            json={"refreshToken": self.refresh_token},
            headers={
                "x-api-key": self.api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        ) as response:
            if response.status >= 400:
                text = await response.text()
                raise ElectroluxAuthError(
                    f"Token refresh failed ({response.status}): {text[:200]}"
                )
            data = await response.json()
        self.access_token = data.get("accessToken") or data.get("access_token") or self.access_token
        self.refresh_token = data.get("refreshToken") or data.get("refresh_token") or self.refresh_token
        if self._on_tokens:
            self._on_tokens(self.access_token, self.refresh_token)

    async def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        url = f"{BASE}{path}"
        for attempt in range(2):
            try:
                async with self._session.request(
                    method, url, json=body, headers=self._headers()
                ) as response:
                    if response.status == 401 and attempt == 0:
                        await self.refresh()
                        continue
                    if response.status >= 400:
                        text = await response.text()
                        raise ApplianceError(f"Electrolux API {response.status}: {text[:240]}")
                    if response.status == 204:
                        return {}
                    return await response.json()
            except ClientResponseError as err:
                raise ApplianceError(str(err)) from err
            except ClientError as err:
                raise ApplianceError(f"Cannot reach Electrolux: {err}") from err
        raise ElectroluxAuthError("Electrolux rejected the access token")

    async def get_appliances(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/appliances")
        if isinstance(data, list):
            return data
        return data.get("appliances") or data.get("data") or []

    async def get_state(self, appliance_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/appliances/{appliance_id}/state")

    async def get_info(self, appliance_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/appliances/{appliance_id}/info")

    async def command(self, appliance_id: str, payload: dict[str, Any]) -> Any:
        return await self._request("PUT", f"/appliances/{appliance_id}/command", payload)

    async def load_program_map(self, appliance_id: str) -> None:
        """Read capabilities and pick programUIDs that exist on this machine."""
        try:
            info = await self.get_info(appliance_id)
        except ApplianceError as err:
            _LOGGER.warning("Could not read appliance capabilities: %s", err)
            self.program_uids = {key: cands[0] for key, cands in PROGRAM_UID_CANDIDATES.items()}
            return
        available = _capability_program_uids(info)
        mapped: dict[str, str] = {}
        for key, candidates in PROGRAM_UID_CANDIDATES.items():
            match = next((uid for uid in candidates if uid in available), None)
            if match is None and available:
                match = next(
                    (
                        uid
                        for uid in available
                        if uid.upper().replace("-", "_") in {c.upper() for c in candidates}
                    ),
                    None,
                )
            mapped[key] = match or candidates[0]
        self.program_uids = mapped
        _LOGGER.debug("Program UID map: %s (available=%s)", mapped, sorted(available))

    async def set_program(
        self,
        appliance_id: str,
        program_key: str,
        extras: set[str] | None = None,
        start_in: int = 0,
    ) -> None:
        uid = self.program_uids.get(program_key) or PROGRAM_UID_CANDIDATES.get(
            program_key, (program_key.upper(),)
        )[0]
        selections: dict[str, Any] = {"programUID": uid}
        for extra in extras or set():
            names = EXTRA_UIDS.get(extra, ())
            if names:
                selections[names[0]] = True
        payload: dict[str, Any] = {"userSelections": selections}
        if start_in > 0:
            payload["startTime"] = int(start_in)
        await self.command(appliance_id, payload)

    async def start(self, appliance_id: str) -> None:
        await self.command(appliance_id, {"executeCommand": "START"})

    async def pause(self, appliance_id: str) -> None:
        await self.command(appliance_id, {"executeCommand": "PAUSE"})

    async def resume(self, appliance_id: str) -> None:
        await self.command(appliance_id, {"executeCommand": "RESUME"})

    async def stop(self, appliance_id: str) -> None:
        await self.command(appliance_id, {"executeCommand": "STOPRESET"})


def _capability_program_uids(info: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    _walk_for_program_uids(info, found)
    return {item for item in found if item}


def _walk_for_program_uids(node: Any, found: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key).endswith("programUID") and isinstance(value, dict):
                values = value.get("values")
                if isinstance(values, dict):
                    found.update(str(item) for item in values)
                elif isinstance(values, list):
                    found.update(str(item) for item in values)
            _walk_for_program_uids(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk_for_program_uids(item, found)


def list_dishwashers(appliances: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Return id/name/type for dishwasher-like appliances."""
    results: list[dict[str, str]] = []
    for item in appliances:
        data = item.get("applianceData") or item
        info = data.get("applianceInfo") if isinstance(data.get("applianceInfo"), dict) else {}
        appliance_id = str(item.get("applianceId") or data.get("applianceId") or "")
        if not appliance_id:
            continue
        appliance_type = str(
            item.get("applianceType") or data.get("applianceType") or data.get("deviceType") or ""
        ).upper()
        name = str(
            data.get("applianceName") or info.get("applianceName") or item.get("applianceName") or appliance_id
        )
        model = str(data.get("modelName") or data.get("model") or info.get("modelName") or "")
        text = f"{name} {model} {appliance_type}".upper()
        if appliance_type in {"DW", "DISHWASHER"} or "DISH" in text or "FSE" in text:
            results.append(
                {"id": appliance_id, "name": name, "model": model or "Dishwasher", "type": appliance_type or "DW"}
            )
    if results:
        return results
    for item in appliances:
        data = item.get("applianceData") or item
        appliance_id = str(item.get("applianceId") or data.get("applianceId") or "")
        if appliance_id:
            results.append(
                {
                    "id": appliance_id,
                    "name": str(data.get("applianceName") or appliance_id),
                    "model": str(data.get("modelName") or ""),
                    "type": str(item.get("applianceType") or ""),
                }
            )
    return results
