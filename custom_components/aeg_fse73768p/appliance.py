"""FSE73768P dishwasher state machine.

Local QuickSelect model used for the card and as a fallback. When Electrolux
credentials are present the coordinator overwrites this from live cloud state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import time
from typing import Any

from .programs import (
    ALL_EXTRAS,
    PHASE_AIRDRY,
    PHASE_LABELS,
    PROGRAM_ORDER,
    PROGRAMS,
    Program,
    ResolvedCycle,
    compatible_extras,
    resolve_cycle,
)

STATE_OFF = "off"
STATE_IDLE = "idle"
STATE_DELAYED = "delayed"
STATE_RUNNING = "running"
STATE_PAUSED = "paused"
STATE_AIRDRY = "airdry"
STATE_COMPLETE = "complete"
STATE_ERROR = "error"

BEAM_OFF = "off"
BEAM_RED = "red"
BEAM_GREEN = "green"
BEAM_FLASH = "flash"

MACHINE_CARE_EVERY = 30
AUTO_OFF_IDLE_SECONDS = 300


class ApplianceError(Exception):
    """User-facing appliance error."""


@dataclass
class Appliance:
    """Offline AEG FSE73768P."""

    name: str = "AEG FSE73768P"
    powered: bool = True
    door_open: bool = False
    program_id: str = "eco"
    extras: set[str] = field(default_factory=set)
    state: str = STATE_IDLE
    phase: str = "idle"
    elapsed_seconds: int = 0
    delay_hours: int = 0
    delay_remaining_seconds: int = 0
    salt_ok: bool = True
    rinse_aid_ok: bool = True
    water_softener: int = 5
    rinse_aid_level: int = 4
    airdry_enabled: bool = True
    end_sound: bool = False
    key_tones: bool = True
    comfort_lift: bool = False
    interior_light_on: bool = False
    cycle_count: int = 0
    cycles_since_care: int = 0
    last_error: str | None = None
    cloud: bool = False
    started_at: float | None = None
    updated_at: float = field(default_factory=time.time)
    _cycle: ResolvedCycle | None = field(default=None, repr=False)
    _last_tick: float = field(default_factory=time.time, repr=False)
    _idle_since: float = field(default_factory=time.time, repr=False)

    # ------------------------------------------------------------------
    # Derived
    # ------------------------------------------------------------------
    @property
    def program(self) -> Program:
        return PROGRAMS[self.program_id]

    @property
    def cycle(self) -> ResolvedCycle:
        if self._cycle is None:
            self._cycle = resolve_cycle(self.program, self.extras)
        return self._cycle

    @property
    def remaining_seconds(self) -> int:
        if self.state == STATE_DELAYED:
            return self.delay_remaining_seconds + self.cycle.duration_min * 60
        if self.state in {STATE_RUNNING, STATE_PAUSED, STATE_AIRDRY}:
            return max(0, self.cycle.duration_min * 60 - self.elapsed_seconds)
        if self.state == STATE_COMPLETE:
            return 0
        return self.cycle.duration_min * 60

    @property
    def progress(self) -> int:
        total = self.cycle.duration_min * 60
        if total <= 0 or self.state in {STATE_OFF, STATE_IDLE, STATE_DELAYED}:
            return 0
        return max(0, min(100, int(self.elapsed_seconds / total * 100)))

    @property
    def beam(self) -> str:
        if not self.powered or self.state in {STATE_OFF, STATE_IDLE, STATE_DELAYED}:
            return BEAM_OFF
        if self.state == STATE_ERROR:
            return BEAM_FLASH
        if self.state == STATE_COMPLETE:
            return BEAM_GREEN
        return BEAM_RED

    @property
    def machine_care_needed(self) -> bool:
        return self.cycles_since_care >= MACHINE_CARE_EVERY

    @property
    def interior_light(self) -> bool:
        return bool(self.powered and self.door_open and self.interior_light_on)

    @property
    def current_phase_label(self) -> str:
        if self.state == STATE_PAUSED:
            return PHASE_LABELS["paused"]
        if self.state == STATE_DELAYED:
            return PHASE_LABELS["delay"]
        return PHASE_LABELS.get(self.phase, self.phase.replace("_", " ").title())

    def energy_used_kwh(self) -> float:
        return round(self.cycle.energy_kwh * (self.progress / 100), 3)

    def water_used_l(self) -> float:
        return round(self.cycle.water_l * (self.progress / 100), 2)

    def current_temperature(self) -> int | None:
        if self.state not in {STATE_RUNNING, STATE_PAUSED, STATE_AIRDRY}:
            return None
        for phase in self.cycle.phases:
            if phase.key == self.phase:
                return phase.temperature_c
        return None

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    def power_on(self) -> None:
        self.powered = True
        if self.state == STATE_OFF:
            self.state = STATE_IDLE
            self.phase = "idle"
        self._touch()

    def power_off(self) -> None:
        if self.state in {STATE_RUNNING, STATE_PAUSED, STATE_DELAYED, STATE_AIRDRY}:
            self.cancel()
        self.powered = False
        self.state = STATE_OFF
        self.phase = "idle"
        self.interior_light_on = False
        self.comfort_lift = False
        self._touch()

    def set_program(self, program_id: str) -> None:
        self._ensure_powered()
        self._ensure_idle_selection()
        if program_id not in PROGRAMS:
            raise ApplianceError(f"Unknown programme: {program_id}")
        self.program_id = program_id
        self.extras = compatible_extras(PROGRAMS[program_id], self.extras)
        self._cycle = None
        self._touch()

    def set_extra(self, extra: str, enabled: bool) -> None:
        self._ensure_powered()
        self._ensure_idle_selection()
        if extra not in ALL_EXTRAS:
            raise ApplianceError(f"Unknown extra: {extra}")
        if extra not in self.program.extras:
            raise ApplianceError(f"{extra} is not available on {self.program.name}")
        updated = set(self.extras)
        if enabled:
            updated.add(extra)
        else:
            updated.discard(extra)
        self.extras = compatible_extras(self.program, updated)
        self._cycle = None
        self._touch()

    def set_door(self, open_: bool) -> None:
        self.door_open = open_
        if open_:
            self.interior_light_on = True
            if self.state == STATE_RUNNING:
                self.pause()
        else:
            self.comfort_lift = False
            self.interior_light_on = False
            if self.state == STATE_PAUSED and self.powered:
                # Closing the door resumes a paused wash, matching the appliance.
                self.resume()
        self._touch()

    def set_delay_hours(self, hours: int) -> None:
        self._ensure_idle_selection()
        if hours < 0 or hours > 24:
            raise ApplianceError("Delay start must be between 0 and 24 hours")
        self.delay_hours = hours
        self._touch()

    def start(self, program_id: str | None = None) -> None:
        self._ensure_powered()
        if self.state in {STATE_RUNNING, STATE_AIRDRY}:
            return
        if self.state == STATE_PAUSED:
            self.resume()
            return
        if self.door_open:
            raise ApplianceError("Close the door before starting a programme")
        if program_id:
            self.set_program(program_id)
        self._cycle = resolve_cycle(self.program, self.extras)
        self.elapsed_seconds = 0
        self.last_error = None
        if self.delay_hours:
            self.state = STATE_DELAYED
            self.phase = "delay"
            self.delay_remaining_seconds = self.delay_hours * 3600
        else:
            self._begin_wash()
        self._touch()

    def pause(self) -> None:
        if self.state == STATE_RUNNING:
            self.state = STATE_PAUSED
            self._touch()

    def resume(self) -> None:
        self._ensure_powered()
        if self.door_open:
            raise ApplianceError("Close the door to resume")
        if self.state == STATE_PAUSED:
            self.state = STATE_AIRDRY if self.phase == PHASE_AIRDRY else STATE_RUNNING
            self._touch()

    def cancel(self) -> None:
        self.state = STATE_IDLE
        self.phase = "idle"
        self.elapsed_seconds = 0
        self.delay_remaining_seconds = 0
        self.delay_hours = 0
        self._cycle = None
        self._idle_since = time.time()
        self._touch()

    def refill_salt(self) -> None:
        self.salt_ok = True
        self._touch()

    def refill_rinse_aid(self) -> None:
        self.rinse_aid_ok = True
        self._touch()

    def reset_machine_care(self) -> None:
        self.cycles_since_care = 0
        self._touch()

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def tick(self, now: float | None = None) -> bool:
        """Advance the machine. Returns True if state changed enough to push."""
        now = now if now is not None else time.time()
        dt = max(0, int(now - self._last_tick))
        self._last_tick = now
        if dt <= 0:
            return False
        changed = False
        if self.state == STATE_DELAYED:
            self.delay_remaining_seconds = max(0, self.delay_remaining_seconds - dt)
            changed = True
            if self.delay_remaining_seconds == 0:
                if self.door_open:
                    self.state = STATE_ERROR
                    self.last_error = "Door open at delayed start"
                else:
                    self._begin_wash()
        elif self.state in {STATE_RUNNING, STATE_AIRDRY}:
            self.elapsed_seconds += dt
            self._sync_phase()
            changed = True
            if self.elapsed_seconds >= self.cycle.duration_min * 60:
                self._complete()
        elif self.state == STATE_IDLE and self.powered and not self.cloud:
            if now - self._idle_since >= AUTO_OFF_IDLE_SECONDS:
                self.power_off()
                changed = True
        if changed:
            self.updated_at = now
        return changed

    def _begin_wash(self) -> None:
        self.state = STATE_RUNNING
        self.elapsed_seconds = 0
        self.started_at = time.time()
        self.delay_hours = 0
        self.delay_remaining_seconds = 0
        self._sync_phase()

    def _sync_phase(self) -> None:
        cursor = 0
        for phase in self.cycle.phases:
            cursor += phase.minutes * 60
            if self.elapsed_seconds < cursor:
                self.phase = phase.key
                if phase.key == PHASE_AIRDRY and self.airdry_enabled:
                    self.state = STATE_AIRDRY
                    self.door_open = True
                    self.interior_light_on = True
                elif self.state == STATE_AIRDRY and phase.key != PHASE_AIRDRY:
                    self.state = STATE_RUNNING
                return
        self.phase = self.cycle.phases[-1].key if self.cycle.phases else "complete"

    def _complete(self) -> None:
        self.state = STATE_COMPLETE
        self.phase = "complete"
        self.elapsed_seconds = self.cycle.duration_min * 60
        self.cycle_count += 1
        if self.program_id == "machine_care":
            self.cycles_since_care = 0
        else:
            self.cycles_since_care += 1
        if self.airdry_enabled:
            self.door_open = True
            self.interior_light_on = True
        self._idle_since = time.time()

    def acknowledge_complete(self) -> None:
        if self.state == STATE_COMPLETE:
            self.state = STATE_IDLE
            self.phase = "idle"
            self.elapsed_seconds = 0
            self._cycle = None
            self._idle_since = time.time()
            self._touch()

    def _ensure_powered(self) -> None:
        if not self.powered or self.state == STATE_OFF:
            self.power_on()

    def _ensure_idle_selection(self) -> None:
        if self.state in {STATE_RUNNING, STATE_PAUSED, STATE_DELAYED, STATE_AIRDRY}:
            raise ApplianceError("Stop the current programme before changing settings")

    def _touch(self) -> None:
        self.updated_at = time.time()
        if self.state == STATE_IDLE:
            self._idle_since = self.updated_at

    # ------------------------------------------------------------------
    # Persistence / card payload
    # ------------------------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        cycle = self.cycle
        return {
            "name": self.name,
            "model": "FSE73768P",
            "pnc": "911438399",
            "series": "7000 ComfortLift",
            "offline": not self.cloud,
            "cloud": self.cloud,
            "powered": self.powered,
            "state": self.state,
            "program": self.program_id,
            "program_name": self.program.name,
            "program_description": self.program.description,
            "phase": self.phase,
            "phase_label": self.current_phase_label,
            "progress": self.progress,
            "remaining_seconds": self.remaining_seconds,
            "elapsed_seconds": self.elapsed_seconds,
            "duration_minutes": cycle.duration_min,
            "wash_temperature": cycle.wash_temp,
            "rinse_temperature": cycle.rinse_temp,
            "current_temperature": self.current_temperature(),
            "door_open": self.door_open,
            "extras": {extra: extra in cycle.extras for extra in ALL_EXTRAS},
            "available_extras": list(self.program.extras),
            "ecometer": cycle.ecometer,
            "beam": self.beam,
            "noise_db": cycle.noise_db,
            "energy_kwh": cycle.energy_kwh,
            "energy_used_kwh": self.energy_used_kwh(),
            "water_l": cycle.water_l,
            "water_used_l": self.water_used_l(),
            "salt_ok": self.salt_ok,
            "rinse_aid_ok": self.rinse_aid_ok,
            "machine_care_needed": self.machine_care_needed,
            "comfort_lift": self.comfort_lift and self.door_open,
            "interior_light": self.interior_light,
            "delay_hours": self.delay_hours,
            "delay_remaining_seconds": self.delay_remaining_seconds,
            "airdry_enabled": self.airdry_enabled,
            "end_sound": self.end_sound,
            "key_tones": self.key_tones,
            "water_softener": self.water_softener,
            "rinse_aid_level": self.rinse_aid_level,
            "cycle_count": self.cycle_count,
            "cycles_since_care": self.cycles_since_care,
            "last_error": self.last_error,
            "started_at": datetime.fromtimestamp(self.started_at, tz=UTC).isoformat()
            if self.started_at
            else None,
            "programs": [
                {
                    "key": key,
                    "name": PROGRAMS[key].name,
                    "duration_min": resolve_cycle(
                        PROGRAMS[key],
                        self.extras if key == self.program_id else set(),
                    ).duration_min,
                    "water_l": PROGRAMS[key].water_l,
                    "energy_kwh": PROGRAMS[key].energy_kwh,
                    "ecometer": PROGRAMS[key].ecometer,
                    "my_time": PROGRAMS[key].my_time,
                    "description": PROGRAMS[key].description,
                    "soil": PROGRAMS[key].soil,
                    "selected": key == self.program_id,
                }
                for key in PROGRAM_ORDER
            ],
        }

    def to_storage(self) -> dict[str, Any]:
        return {
            "powered": self.powered,
            "door_open": self.door_open,
            "program_id": self.program_id,
            "extras": sorted(self.extras),
            "salt_ok": self.salt_ok,
            "rinse_aid_ok": self.rinse_aid_ok,
            "water_softener": self.water_softener,
            "rinse_aid_level": self.rinse_aid_level,
            "airdry_enabled": self.airdry_enabled,
            "end_sound": self.end_sound,
            "key_tones": self.key_tones,
            "cycle_count": self.cycle_count,
            "cycles_since_care": self.cycles_since_care,
        }

    def restore(self, data: dict[str, Any]) -> None:
        self.powered = data.get("powered", True)
        self.door_open = data.get("door_open", False)
        self.program_id = data.get("program_id", "eco")
        if self.program_id not in PROGRAMS:
            self.program_id = "eco"
        self.extras = set(data.get("extras", []))
        self.salt_ok = data.get("salt_ok", True)
        self.rinse_aid_ok = data.get("rinse_aid_ok", True)
        self.water_softener = int(data.get("water_softener", 5))
        self.rinse_aid_level = int(data.get("rinse_aid_level", 4))
        self.airdry_enabled = data.get("airdry_enabled", True)
        self.end_sound = data.get("end_sound", False)
        self.key_tones = data.get("key_tones", True)
        self.cycle_count = int(data.get("cycle_count", 0))
        self.cycles_since_care = int(data.get("cycles_since_care", 0))
        self.state = STATE_IDLE if self.powered else STATE_OFF
        self.phase = "idle"
        self._cycle = None
        self._last_tick = time.time()
