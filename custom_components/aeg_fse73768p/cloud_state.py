"""Map Electrolux dishwasher state onto the local FSE73768P model."""

from __future__ import annotations

from typing import Any

from .appliance import (
    STATE_AIRDRY,
    STATE_COMPLETE,
    STATE_DELAYED,
    STATE_ERROR,
    STATE_IDLE,
    STATE_OFF,
    STATE_PAUSED,
    STATE_RUNNING,
    Appliance,
)
from .electrolux import PROGRAM_UID_CANDIDATES
from .programs import PHASE_AIRDRY

STATE_FROM_CLOUD = {
    "OFF": STATE_OFF,
    "IDLE": STATE_IDLE,
    "READY_TO_START": STATE_IDLE,
    "RUNNING": STATE_RUNNING,
    "PAUSED": STATE_PAUSED,
    "DELAYED_START": STATE_DELAYED,
    "END_OF_CYCLE": STATE_COMPLETE,
    "ERROR": STATE_ERROR,
}

PHASE_FROM_CLOUD = {
    "PREWASH": "prewash",
    "PRE_WASH": "prewash",
    "WASHING": "main_wash",
    "MAINWASH": "main_wash",
    "MAIN_WASH": "main_wash",
    "RINSING": "intermediate_rinse",
    "INTERMEDIATE_RINSE": "intermediate_rinse",
    "FINALRINSE": "final_rinse",
    "FINAL_RINSE": "final_rinse",
    "DRYING": "drying",
    "AIRDRY": PHASE_AIRDRY,
    "AIR_DRY": PHASE_AIRDRY,
    "DOOR_OPENING": PHASE_AIRDRY,
    "END": "complete",
}


def reported_state(payload: dict[str, Any]) -> dict[str, Any]:
    props = payload.get("properties") or payload
    reported = props.get("reported") if isinstance(props, dict) else None
    return reported if isinstance(reported, dict) else payload


def apply_cloud_state(appliance: Appliance, payload: dict[str, Any]) -> None:
    """Overwrite local fields from a live Electrolux state document."""
    reported = reported_state(payload)
    raw_state = str(reported.get("applianceState") or reported.get("status") or "IDLE").upper()
    appliance.state = STATE_FROM_CLOUD.get(raw_state, STATE_IDLE)
    if appliance.state == STATE_RUNNING:
        phase_raw = str(reported.get("cyclePhase") or reported.get("phase") or "").upper()
        appliance.phase = PHASE_FROM_CLOUD.get(phase_raw, "main_wash")
        if appliance.phase == PHASE_AIRDRY:
            appliance.state = STATE_AIRDRY
    elif appliance.state == STATE_COMPLETE:
        appliance.phase = "complete"
    elif appliance.state == STATE_DELAYED:
        appliance.phase = "delay"
    elif appliance.state == STATE_PAUSED:
        appliance.phase = "paused"
    else:
        appliance.phase = "idle"

    remaining = reported.get("timeToEnd") or reported.get("timeRemaining") or 0
    try:
        remaining_s = int(remaining)
    except (TypeError, ValueError):
        remaining_s = 0
    if remaining_s > 100000:
        remaining_s = remaining_s // 1000
    appliance.elapsed_seconds = max(0, appliance.cycle.duration_min * 60 - remaining_s)

    delay = reported.get("startTime") or 0
    try:
        delay_s = int(delay)
    except (TypeError, ValueError):
        delay_s = 0
    if delay_s in (-1, 0):
        appliance.delay_hours = 0
        appliance.delay_remaining_seconds = 0
    else:
        appliance.delay_remaining_seconds = max(0, delay_s)
        appliance.delay_hours = max(0, delay_s // 3600)

    door = str(reported.get("doorState") or "").upper()
    appliance.door_open = door in {"OPEN", "AJAR", "OPENED"}
    appliance.powered = appliance.state != STATE_OFF

    selections = reported.get("userSelections") or {}
    if isinstance(selections, dict):
        program_uid = str(selections.get("programUID") or selections.get("programId") or "")
        mapped = program_from_uid(program_uid)
        if mapped:
            appliance.program_id = mapped
            appliance._cycle = None
        extras: set[str] = set()
        for key, enabled in selections.items():
            if not enabled:
                continue
            low = str(key).lower()
            if "extrapower" in low:
                extras.add("extra_power")
            if "glasscare" in low:
                extras.add("glass_care")
            if "silent" in low:
                extras.add("extra_silent")
        appliance.extras = extras

    alerts = reported.get("alerts") or reported.get("alertList") or []
    if isinstance(alerts, dict):
        alerts = [name for name, on in alerts.items() if on]
    alert_text = " ".join(str(item).upper() for item in alerts)
    appliance.salt_ok = "SALT" not in alert_text
    appliance.rinse_aid_ok = "RINSE" not in alert_text
    if "MACHINE_CARE" in alert_text or "MACHINECARE" in alert_text:
        appliance.cycles_since_care = 30

    hardness = reported.get("waterHardness")
    if hardness is not None:
        try:
            appliance.water_softener = max(1, min(10, int(hardness)))
        except (TypeError, ValueError):
            pass

    appliance.last_error = None
    connection = str(reported.get("connectionState") or "").upper()
    if connection in {"DISCONNECTED", "OFFLINE"}:
        appliance.last_error = "Dishwasher is not connected"
    remote = str(reported.get("remoteControl") or "")
    if remote.upper() in {"DISABLED", "TEMPORARY_LOCKED"}:
        appliance.last_error = "Enable remote start on the dishwasher door"
    appliance._touch()


def program_from_uid(uid: str) -> str | None:
    if not uid:
        return None
    needle = uid.upper().replace("-", "_")
    for key, candidates in PROGRAM_UID_CANDIDATES.items():
        if needle in {c.upper() for c in candidates} or needle == key.upper():
            return key
    return None
