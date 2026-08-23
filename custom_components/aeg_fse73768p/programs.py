"""AEG FSE73768P QuickSelect programme catalogue.

Values follow the 7000-series ComfortLift / QuickSelect manuals (FSE737xxP
family): MY TIME programmes, AUTO Sense, Machine Care, and EXTRAS.
ECO consumption is the Ecodesign (EU) 2019/2022 rated cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

PHASE_PREWASH = "prewash"
PHASE_MAIN_WASH = "main_wash"
PHASE_INTERMEDIATE_RINSE = "intermediate_rinse"
PHASE_FINAL_RINSE = "final_rinse"
PHASE_DRYING = "drying"
PHASE_AIRDRY = "airdry"

EXTRA_POWER = "extra_power"
GLASS_CARE = "glass_care"
EXTRA_SILENT = "extra_silent"

ALL_EXTRAS: Final[tuple[str, ...]] = (EXTRA_POWER, GLASS_CARE, EXTRA_SILENT)


@dataclass(frozen=True, slots=True)
class Phase:
    """One phase of a wash cycle."""

    key: str
    minutes: int
    temperature_c: int | None = None


@dataclass(frozen=True, slots=True)
class Program:
    """A factory programme on the FSE73768P."""

    key: str
    name: str
    duration_min: int
    water_l: float
    energy_kwh: float
    ecometer: int
    soil: str
    load: str
    extras: tuple[str, ...]
    phases: tuple[Phase, ...]
    noise_db: int = 39
    description: str = ""
    my_time: bool = False


def _prog(
    key: str,
    name: str,
    duration_min: int,
    water_l: float,
    energy_kwh: float,
    ecometer: int,
    soil: str,
    load: str,
    extras: tuple[str, ...],
    phases: tuple[Phase, ...],
    *,
    noise_db: int = 39,
    description: str = "",
    my_time: bool = False,
) -> Program:
    total = sum(p.minutes for p in phases)
    if total != duration_min:
        raise ValueError(f"{key}: phase minutes {total} != duration {duration_min}")
    return Program(
        key=key,
        name=name,
        duration_min=duration_min,
        water_l=water_l,
        energy_kwh=energy_kwh,
        ecometer=ecometer,
        soil=soil,
        load=load,
        extras=extras,
        phases=phases,
        noise_db=noise_db,
        description=description,
        my_time=my_time,
    )


PROGRAMS: Final[dict[str, Program]] = {
    "quick": _prog(
        "quick",
        "Quick",
        30,
        10.6,
        0.58,
        2,
        "Fresh, light soil",
        "Crockery and cutlery",
        (EXTRA_POWER, GLASS_CARE),
        (
            Phase(PHASE_MAIN_WASH, 18, 50),
            Phase(PHASE_INTERMEDIATE_RINSE, 5),
            Phase(PHASE_FINAL_RINSE, 5, 45),
            Phase(PHASE_AIRDRY, 2),
        ),
        description="Shortest MY TIME cycle — 30 minutes for a lightly soiled load.",
        my_time=True,
    ),
    "1h": _prog(
        "1h",
        "1h",
        60,
        11.7,
        0.99,
        3,
        "Fresh, lightly dried-on",
        "Crockery and cutlery",
        (EXTRA_POWER, GLASS_CARE),
        (
            Phase(PHASE_MAIN_WASH, 40, 60),
            Phase(PHASE_INTERMEDIATE_RINSE, 6),
            Phase(PHASE_FINAL_RINSE, 8, 50),
            Phase(PHASE_AIRDRY, 6),
        ),
        description="One-hour MY TIME cycle for fresh and lightly dried-on soil.",
        my_time=True,
    ),
    "1h30": _prog(
        "1h30",
        "1h 30min",
        90,
        12.9,
        1.08,
        3,
        "Normal, lightly dried-on",
        "Crockery, cutlery, pots and pans",
        (EXTRA_POWER, GLASS_CARE),
        (
            Phase(PHASE_MAIN_WASH, 50, 60),
            Phase(PHASE_INTERMEDIATE_RINSE, 8),
            Phase(PHASE_FINAL_RINSE, 10, 55),
            Phase(PHASE_DRYING, 15),
            Phase(PHASE_AIRDRY, 7),
        ),
        description="Wash and dry a normally soiled load in 90 minutes.",
        my_time=True,
    ),
    "2h40": _prog(
        "2h40",
        "2h 40min",
        160,
        12.3,
        1.19,
        4,
        "Normal to heavy, dried-on",
        "Crockery, cutlery, pots and pans",
        (EXTRA_POWER, GLASS_CARE),
        (
            Phase(PHASE_PREWASH, 15),
            Phase(PHASE_MAIN_WASH, 80, 60),
            Phase(PHASE_INTERMEDIATE_RINSE, 10),
            Phase(PHASE_FINAL_RINSE, 15, 60),
            Phase(PHASE_DRYING, 30),
            Phase(PHASE_AIRDRY, 10),
        ),
        description="Longer MY TIME cycle for heavily soiled pots and pans.",
        my_time=True,
    ),
    "eco": _prog(
        "eco",
        "ECO",
        240,
        11.0,
        0.86,
        5,
        "Normal, lightly dried-on",
        "Crockery, cutlery, pots and pans",
        (EXTRA_POWER, GLASS_CARE, EXTRA_SILENT),
        (
            Phase(PHASE_PREWASH, 20),
            Phase(PHASE_MAIN_WASH, 120, 50),
            Phase(PHASE_INTERMEDIATE_RINSE, 15),
            Phase(PHASE_FINAL_RINSE, 20, 55),
            Phase(PHASE_DRYING, 50),
            Phase(PHASE_AIRDRY, 15),
        ),
        description="Rated ECO cycle — most efficient water and energy use (4 hours).",
        my_time=True,
    ),
    "auto_sense": _prog(
        "auto_sense",
        "AUTO Sense",
        145,
        11.9,
        0.99,
        4,
        "All soil levels",
        "Crockery, cutlery, pots and pans",
        (),
        (
            Phase(PHASE_PREWASH, 10),
            Phase(PHASE_MAIN_WASH, 70, 55),
            Phase(PHASE_INTERMEDIATE_RINSE, 10),
            Phase(PHASE_FINAL_RINSE, 15, 60),
            Phase(PHASE_DRYING, 30),
            Phase(PHASE_AIRDRY, 10),
        ),
        description="Sensors adjust temperature, water and duration to the load.",
    ),
    "machine_care": _prog(
        "machine_care",
        "Machine Care",
        60,
        10.8,
        0.67,
        3,
        "Appliance interior",
        "Empty appliance",
        (),
        (
            Phase(PHASE_MAIN_WASH, 40, 70),
            Phase(PHASE_INTERMEDIATE_RINSE, 8),
            Phase(PHASE_FINAL_RINSE, 8, 70),
            Phase(PHASE_AIRDRY, 4),
        ),
        description="Cleans limescale and grease from the tub. Do not load dishes.",
    ),
}

PROGRAM_ORDER: Final[tuple[str, ...]] = (
    "quick",
    "1h",
    "1h30",
    "2h40",
    "eco",
    "auto_sense",
    "machine_care",
)

EXTRA_LABELS: Final[dict[str, str]] = {
    EXTRA_POWER: "ExtraPower",
    GLASS_CARE: "GlassCare",
    EXTRA_SILENT: "ExtraSilent",
}

PHASE_LABELS: Final[dict[str, str]] = {
    "idle": "Idle",
    "delay": "Delayed start",
    PHASE_PREWASH: "Prewash",
    PHASE_MAIN_WASH: "Main wash",
    PHASE_INTERMEDIATE_RINSE: "Intermediate rinse",
    PHASE_FINAL_RINSE: "Final rinse",
    PHASE_DRYING: "Drying",
    PHASE_AIRDRY: "AirDry",
    "complete": "Complete",
    "paused": "Paused",
}


@dataclass(slots=True)
class ResolvedCycle:
    """A programme after EXTRAS have been applied."""

    program: Program
    extras: tuple[str, ...]
    duration_min: int
    water_l: float
    energy_kwh: float
    ecometer: int
    noise_db: int
    wash_temp: int | None
    rinse_temp: int | None
    phases: tuple[Phase, ...] = field(default_factory=tuple)


def compatible_extras(program: Program, extras: set[str]) -> set[str]:
    """Return extras that are valid together for this programme."""
    allowed = {extra for extra in extras if extra in program.extras}
    if EXTRA_POWER in allowed and GLASS_CARE in allowed:
        # ExtraPower raises temperature; GlassCare caps it at 45 °C.
        allowed.remove(EXTRA_POWER)
    if EXTRA_SILENT in allowed and EXTRA_POWER in allowed:
        allowed.remove(EXTRA_SILENT)
    return allowed


def resolve_cycle(program: Program, extras: set[str]) -> ResolvedCycle:
    """Apply EXTRAS to duration, temperatures, water and energy."""
    selected = tuple(extra for extra in ALL_EXTRAS if extra in compatible_extras(program, extras))
    duration = program.duration_min
    water = program.water_l
    energy = program.energy_kwh
    noise = program.noise_db
    ecometer = program.ecometer
    phases = list(program.phases)

    def _bump_phase(key: str, minutes: int, temp_delta: int = 0, temp_set: int | None = None) -> None:
        nonlocal phases
        updated: list[Phase] = []
        for phase in phases:
            if phase.key == key:
                new_temp = phase.temperature_c
                if temp_set is not None:
                    new_temp = temp_set
                elif new_temp is not None and temp_delta:
                    new_temp = new_temp + temp_delta
                updated.append(Phase(phase.key, phase.minutes + minutes, new_temp))
            else:
                updated.append(phase)
        phases = updated

    if EXTRA_POWER in selected:
        duration = round(duration * 1.15)
        extra_min = duration - program.duration_min
        _bump_phase(PHASE_MAIN_WASH, extra_min, temp_delta=5)
        energy = round(energy * 1.18, 3)
        water = round(water * 1.04, 2)
        ecometer = max(1, ecometer - 1)
    if GLASS_CARE in selected:
        _bump_phase(PHASE_MAIN_WASH, 0, temp_set=45)
        energy = round(energy * 0.92, 3)
        ecometer = min(5, ecometer + 1)
    if EXTRA_SILENT in selected:
        duration = round(duration * 1.25)
        extra_min = duration - sum(p.minutes for p in phases)
        _bump_phase(PHASE_MAIN_WASH, extra_min)
        noise = 37
        energy = round(energy * 0.95, 3)

    # Keep phase minutes in sync with advertised duration.
    phase_total = sum(p.minutes for p in phases)
    if phase_total != duration and phases:
        last = phases[-1]
        phases[-1] = Phase(last.key, last.minutes + (duration - phase_total), last.temperature_c)

    wash_temp = next((p.temperature_c for p in phases if p.key == PHASE_MAIN_WASH), None)
    rinse_temp = next((p.temperature_c for p in phases if p.key == PHASE_FINAL_RINSE), None)

    return ResolvedCycle(
        program=program,
        extras=selected,
        duration_min=sum(p.minutes for p in phases),
        water_l=water,
        energy_kwh=energy,
        ecometer=ecometer,
        noise_db=noise,
        wash_temp=wash_temp,
        rinse_temp=rinse_temp,
        phases=tuple(phases),
    )
