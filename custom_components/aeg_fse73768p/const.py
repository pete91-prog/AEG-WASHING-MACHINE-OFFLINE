"""Constants for the AEG FSE73768P integration."""

from __future__ import annotations

from pathlib import Path
from typing import Final

DOMAIN: Final = "aeg_fse73768p"
MANUFACTURER: Final = "AEG"
MODEL: Final = "FSE73768P"
MODEL_ID: Final = "911438399"
ATTRIBUTION: Final = "AEG FSE73768P via Electrolux Group API"

PLATFORMS: Final = [
    "binary_sensor",
    "button",
    "number",
    "select",
    "sensor",
    "switch",
]

URL_BASE: Final = f"/{DOMAIN}"
CARD_FILENAME: Final = "aeg-fse73768p-card.js"
CONF_NAME: Final = "name"
DEFAULT_NAME: Final = "AEG FSE73768P"
CONF_API_KEY: Final = "api_key"
CONF_ACCESS_TOKEN: Final = "access_token"
CONF_REFRESH_TOKEN: Final = "refresh_token"
CONF_APPLIANCE_ID: Final = "appliance_id"

INTEGRATION_PATH: Final = Path(__file__).parent
