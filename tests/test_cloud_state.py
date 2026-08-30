"""Tests for Electrolux state mapping."""

from __future__ import annotations

from aeg_fse73768p.appliance import STATE_COMPLETE, STATE_RUNNING, Appliance
from aeg_fse73768p.cloud_state import apply_cloud_state, program_from_uid
from aeg_fse73768p.electrolux import _capability_program_uids, list_dishwashers


def test_program_from_uid() -> None:
    assert program_from_uid("ECO") == "eco"
    assert program_from_uid("ECO50") == "eco"
    assert program_from_uid("QUICK30") == "quick"
    assert program_from_uid("AUTO") == "auto_sense"
    assert program_from_uid("MACHINE_CARE") == "machine_care"
    assert program_from_uid("PREWASH") == "prewash"
    assert program_from_uid("PRECAST") == "prewash"


def test_apply_running_state() -> None:
    machine = Appliance()
    apply_cloud_state(
        machine,
        {
            "properties": {
                "reported": {
                    "applianceState": "RUNNING",
                    "cyclePhase": "MAIN_WASH",
                    "timeToEnd": 3600,
                    "doorState": "CLOSED",
                    "userSelections": {"programUID": "ECO"},
                    "remoteControl": "ENABLED",
                    "alerts": [],
                }
            }
        },
    )
    assert machine.state == STATE_RUNNING
    assert machine.phase == "main_wash"
    assert machine.program_id == "eco"
    assert machine.door_open is False
    assert machine.snapshot()["model"] == "FSE73768P"


def test_apply_finished_and_salt_alert() -> None:
    machine = Appliance()
    apply_cloud_state(
        machine,
        {
            "reported": {
                "applianceState": "END_OF_CYCLE",
                "doorState": "OPEN",
                "alerts": ["SALT"],
            }
        },
    )
    assert machine.state == STATE_COMPLETE
    assert machine.door_open is True
    assert machine.salt_ok is False


def test_list_dishwashers_filters_dw() -> None:
    found = list_dishwashers(
        [
            {
                "applianceId": "dw-1",
                "applianceType": "DW",
                "applianceData": {"applianceName": "Kitchen", "modelName": "FSE73768P"},
            },
            {
                "applianceId": "ov-1",
                "applianceType": "OV",
                "applianceData": {"applianceName": "Oven"},
            },
        ]
    )
    assert [item["id"] for item in found] == ["dw-1"]


def test_capability_slash_path_program_uids() -> None:
    found = _capability_program_uids(
        {
            "capabilities": {
                "userSelections/programUID": {
                    "access": "readwrite",
                    "values": {"ECO": {}, "QUICK30": {}, "AUTO": {}},
                }
            }
        }
    )
    assert found == {"ECO", "QUICK30", "AUTO"}


def test_apply_maps_extras_and_remote_lock() -> None:
    machine = Appliance()
    apply_cloud_state(
        machine,
        {
            "properties": {
                "reported": {
                    "applianceState": "IDLE",
                    "userSelections": {
                        "programUID": "ECO",
                        "extraPower": True,
                        "glassCare": False,
                    },
                    "remoteControl": "DISABLED",
                    "waterHardness": 7,
                }
            }
        },
    )
    assert machine.program_id == "eco"
    assert machine.extras == {"extra_power"}
    assert machine.water_softener == 7
    assert machine.last_error and "remote start" in machine.last_error.lower()


def test_card_detects_cloud_machine() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "aeg_fse73768p"
        / "frontend"
        / "aeg-fse73768p-card.js"
    ).read_text(encoding="utf-8")
    assert "st.attributes?.offline === true" not in source
    assert "st.attributes?.model === \"FSE73768P\"" in source
