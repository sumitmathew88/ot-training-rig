"""
otlab.field  -  Purdue Level 0 (instrumentation) + Level 1 (BPCS / SIS).

Each FieldUnit bundles:
  * Level 0 : a first-principles process model (separator vessel) plus the
              field instruments and final elements (valve, pump). Sensor
              readings pass through a transmitter layer that supports
              SPOOFING (for cyber training) and noise.
  * Level 1 : a Basic Process Control System (PID level control + alarms) and
              a SEPARATE Safety Instrumented System / plant-trip (High-High
              ESD), reflecting the BPCS/SIS independence good OT design needs.
              The SIS can be BYPASSED (maintenance override) - which is also a
              juicy attack target in training.

No real plant is touched. This is a simulation.
"""

from dataclasses import dataclass, field
import math
import random


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


# Alarm / trip thresholds (% level)
LL, L, H, HH = 10.0, 20.0, 80.0, 90.0


@dataclass
class Transmitter:
    """Level 0 instrument. Real value in, reported value out.

    `spoof` lets a training scenario freeze/forge the value the controller
    sees while the true process keeps moving - the classic Stuxnet-style
    'lie to the operator' attack.
    """
    noise: float = 0.4
    spoof_active: bool = False
    spoof_value: float = 0.0

    def read(self, true_value: float) -> float:
        if self.spoof_active:
            return self.spoof_value
        return true_value + random.uniform(-self.noise, self.noise)


class PID:
    def __init__(self, kp, ki, kd, dt, lo=0.0, hi=100.0):
        self.kp, self.ki, self.kd, self.dt = kp, ki, kd, dt
        self.lo, self.hi = lo, hi
        self.integ = 0.0
        self.prev = 0.0

    def step(self, sp, pv):
        err = sp - pv
        self.integ += err * self.dt
        deriv = (err - self.prev) / self.dt
        self.prev = err
        out = self.kp * err + self.ki * self.integ + self.kd * deriv
        if out > self.hi:
            out, self.integ = self.hi, self.integ - err * self.dt
        elif out < self.lo:
            out, self.integ = self.lo, self.integ - err * self.dt
        return out


@dataclass
class FieldUnit:
    """One separator skid = Level 0 process + Level 1 controller/SIS."""
    tag: str                       # e.g. "V-101"
    site: str                      # e.g. "ROMA-CSG"
    dt: float = 0.1

    # --- Level 0 true process state ---
    level: float = 50.0            # %
    pressure: float = 350.0        # kPa
    inflow: float = 0.0            # m3/h
    outflow: float = 0.0           # m3/h
    upstream_p: float = 600.0      # kPa supply (well/manifold)
    _area: float = 22.0

    # --- Level 0 instruments / final elements ---
    lt: Transmitter = field(default_factory=Transmitter)   # level transmitter
    pt: Transmitter = field(default_factory=lambda: Transmitter(noise=2.0))

    # --- Level 1 BPCS setpoints / outputs ---
    level_sp: float = 50.0
    auto: bool = True
    valve_manual: float = 0.0
    valve_mv: float = 0.0
    pump_cmd: bool = True
    pump_run: bool = False

    # --- Level 1 SIS (plant trip) ---
    sis_trip: bool = False
    sis_bypass: bool = False       # maintenance override / attack target
    reset_cmd: bool = False

    # --- alarms ---
    alm_LL: bool = False
    alm_L: bool = False
    alm_H: bool = False
    alm_HH: bool = False

    def __post_init__(self):
        self._pid = PID(4.0, 0.8, 0.2, self.dt)

    # ---- Level 0 physics ----
    def _process_step(self):
        dp = max(self.upstream_p - self.pressure, 0.0)
        self.inflow = (self.valve_mv / 100.0) * 80.0 * math.sqrt(dp / 600.0)
        self.outflow = (42.0 * (0.6 + self.level / 250.0)) if self.pump_run else 0.0
        self.level = clamp(self.level + (self.inflow - self.outflow) * self.dt / self._area, 0.0, 100.0)
        self.pressure = 300.0 + self.level * 0.9 + random.uniform(-1.5, 1.5)

    # ---- Level 1 scan ----
    def scan(self):
        # Controller sees instruments, NOT the true value (spoofable)
        lvl_meas = self.lt.read(self.level)

        self.alm_LL = lvl_meas <= LL
        self.alm_L = lvl_meas <= L
        self.alm_H = lvl_meas >= H
        self.alm_HH = lvl_meas >= HH

        # SIS: independent High-High plant trip (unless bypassed)
        if self.alm_HH and not self.sis_bypass:
            self.sis_trip = True
        if self.reset_cmd and lvl_meas < H:
            self.sis_trip = False
            self.reset_cmd = False

        # BPCS inlet valve output
        if self.sis_trip:
            self.valve_mv = 0.0
        elif self.auto:
            self.valve_mv = self._pid.step(self.level_sp, lvl_meas)
        else:
            self.valve_mv = clamp(self.valve_manual, 0.0, 100.0)

        self.pump_run = bool(self.pump_cmd) and not self.alm_LL
        self._process_step()
        return lvl_meas

    # ---- tag snapshot used by OPC server / historian ----
    def snapshot(self, lvl_meas):
        return {
            "Level_PV": round(lvl_meas, 2),
            "Level_TRUE": round(self.level, 2),
            "Pressure_PV": round(self.pt.read(self.pressure), 1),
            "Inflow": round(self.inflow, 2),
            "Outflow": round(self.outflow, 2),
            "Valve_MV": round(self.valve_mv, 2),
            "Pump_Run": self.pump_run,
            "SIS_Trip": self.sis_trip,
            "SIS_Bypass": self.sis_bypass,
            "Alarm_LL": self.alm_LL, "Alarm_L": self.alm_L,
            "Alarm_H": self.alm_H, "Alarm_HH": self.alm_HH,
            "Level_SP": round(self.level_sp, 1),
            "Mode_Auto": self.auto,
            "Valve_Manual": round(self.valve_manual, 1),
            "Pump_Cmd": self.pump_cmd,
        }

    WRITABLE = {"Level_SP", "Mode_Auto", "Valve_Manual", "Pump_Cmd",
                "Reset_Cmd", "SIS_Bypass"}

    def apply_write(self, name, value):
        if name == "Level_SP":
            self.level_sp = float(value)
        elif name == "Mode_Auto":
            self.auto = bool(value)
        elif name == "Valve_Manual":
            self.valve_manual = float(value)
        elif name == "Pump_Cmd":
            self.pump_cmd = bool(value)
        elif name == "Reset_Cmd":
            self.reset_cmd = bool(value)
        elif name == "SIS_Bypass":
            self.sis_bypass = bool(value)
