"""Unit tests for the FSE73768P programme model."""

from __future__ import annotations

import pytest

from aeg_fse73768p.appliance import (
    STATE_AIRDRY,
    STATE_COMPLETE,
    STATE_DELAYED,
    STATE_IDLE,
    STATE_OFF,
    STATE_PAUSED,
    STATE_RUNNING,
    Appliance,
    ApplianceError,
)
from aeg_fse73768p.programs import PROGRAM_ORDER, PROGRAMS, resolve_cycle


def test_all_programmes_are_present() -> None:
    assert PROGRAM_ORDER == (
        "quick",
        "1h",
        "1h30",
        "2h40",
        "eco",
        "auto_sense",
        "machine_care",
    )
    for key in PROGRAM_ORDER:
        program = PROGRAMS[key]
        assert sum(phase.minutes for phase in program.phases) == program.duration_min


def test_eco_is_the_rated_cycle() -> None:
    eco = PROGRAMS["eco"]
    assert eco.duration_min == 240
    assert eco.water_l == 11.0
    assert eco.energy_kwh == 0.86
    assert eco.ecometer == 5
    assert "extra_silent" in eco.extras


def test_start_requires_closed_door() -> None:
    machine = Appliance()
    machine.set_door(True)
    with pytest.raises(ApplianceError, match="Close the door"):
        machine.start("quick")


def test_quick_start_and_progress() -> None:
    machine = Appliance()
    machine.start("quick")
    assert machine.state == STATE_RUNNING
    assert machine.phase == "main_wash"
    machine.tick(machine._last_tick + 18 * 60)
    assert machine.phase == "intermediate_rinse"
    machine.tick(machine._last_tick + 12 * 60)
    assert machine.state == STATE_COMPLETE
    assert machine.cycle_count == 1
    assert machine.remaining_seconds == 0


def test_opening_door_pauses_and_closing_resumes() -> None:
    machine = Appliance()
    machine.start("1h")
    machine.set_door(True)
    assert machine.state == STATE_PAUSED
    machine.set_door(False)
    assert machine.state == STATE_RUNNING


def test_extra_power_increases_duration_and_temperature() -> None:
    base = resolve_cycle(PROGRAMS["1h30"], set())
    boosted = resolve_cycle(PROGRAMS["1h30"], {"extra_power"})
    assert boosted.duration_min > base.duration_min
    assert boosted.wash_temp == (base.wash_temp or 0) + 5


def test_glass_care_caps_wash_at_45() -> None:
    cycle = resolve_cycle(PROGRAMS["quick"], {"glass_care"})
    assert cycle.wash_temp == 45
    assert "extra_power" not in cycle.extras


def test_extra_silent_only_on_eco() -> None:
    machine = Appliance()
    machine.set_program("quick")
    with pytest.raises(ApplianceError):
        machine.set_extra("extra_silent", True)
    machine.set_program("eco")
    machine.set_extra("extra_silent", True)
    assert "extra_silent" in machine.extras
    assert machine.cycle.noise_db == 37


def test_auto_sense_and_machine_care_have_no_extras() -> None:
    assert PROGRAMS["auto_sense"].extras == ()
    assert PROGRAMS["machine_care"].extras == ()


def test_delay_start() -> None:
    machine = Appliance()
    machine.set_delay_hours(2)
    machine.start("eco")
    assert machine.state == STATE_DELAYED
    machine.tick(machine._last_tick + 2 * 3600)
    assert machine.state == STATE_RUNNING
    assert machine.program_id == "eco"


def test_airdry_opens_the_door() -> None:
    machine = Appliance()
    machine.start("quick")
    # Jump to the AirDry tail of Quick (last 2 minutes).
    machine.tick(machine._last_tick + 28 * 60)
    assert machine.phase == "airdry"
    assert machine.state == STATE_AIRDRY
    assert machine.door_open is True
    assert machine.interior_light is True


def test_machine_care_resets_counter() -> None:
    machine = Appliance()
    machine.cycles_since_care = 30
    assert machine.machine_care_needed is True
    machine.start("machine_care")
    machine.tick(machine._last_tick + 60 * 60)
    assert machine.state == STATE_COMPLETE
    assert machine.machine_care_needed is False


def test_power_off_cancels_a_run() -> None:
    machine = Appliance()
    machine.start("eco")
    machine.power_off()
    assert machine.state == STATE_OFF
    assert machine.elapsed_seconds == 0


def test_snapshot_lists_every_programme() -> None:
    payload = Appliance().snapshot()
    assert payload["model"] == "FSE73768P"
    assert [item["key"] for item in payload["programs"]] == list(PROGRAM_ORDER)


def test_cannot_change_programme_while_running() -> None:
    machine = Appliance()
    machine.start("eco")
    with pytest.raises(ApplianceError):
        machine.set_program("quick")


def test_restore_does_not_resume_a_mid_cycle() -> None:
    machine = Appliance()
    machine.restore(
        {
            "powered": True,
            "program_id": "2h40",
            "extras": ["glass_care"],
            "cycle_count": 9,
        }
    )
    assert machine.state == STATE_IDLE
    assert machine.program_id == "2h40"
    assert machine.cycle_count == 9
    assert "glass_care" in machine.extras


def test_frontend_imports_parent_const() -> None:
    """A wrong relative import here breaks HA config flow with Invalid handler."""
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "aeg_fse73768p"
        / "frontend"
        / "__init__.py"
    ).read_text(encoding="utf-8")
    assert "from ..const import" in source
    assert "from .const import" not in source
