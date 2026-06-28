"""
otlab.platform  -  the layers above Level 1.

  EventBus     : shared alarm/security/training event stream.
  Historian    : Purdue L4/5, an IP21-style time-series store (SQLite) plus
                 simple production/availability KPIs.
  SIEMMonitor  : Purdue L3.2, rule-based detection of OT anomalies and
                 attacks (unauthorised writes, SIS bypass, transmitter
                 spoofing via mass-balance plausibility, alarm floods,
                 comms loss).
  ScenarioEngine: the training layer - timed process+cyber injects, learner
                 objectives, and scoring.
"""

import json
import sqlite3
import threading
import time
from collections import deque


# --------------------------------------------------------------------------
class EventBus:
    def __init__(self, maxlen=500):
        self.events = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def emit(self, kind, source, message, severity="INFO"):
        ev = {"ts": time.time(), "kind": kind, "source": source,
              "message": message, "severity": severity}
        with self._lock:
            self.events.append(ev)
        return ev

    def recent(self, n=60):
        with self._lock:
            return list(self.events)[-n:][::-1]


# --------------------------------------------------------------------------
class Historian:
    """L4/5 process historian (IP21 analogue)."""

    def __init__(self, path=":memory:"):
        self.path = path
        self._lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("""CREATE TABLE IF NOT EXISTS hist(
            ts REAL, site TEXT, level REAL, pressure REAL, inflow REAL,
            outflow REAL, valve REAL, pump INT, sis INT, alarms INT)""")
        self.db.commit()

    def record(self, snap):
        alarms = sum(int(snap.get(k, False)) for k in
                     ("Alarm_LL", "Alarm_L", "Alarm_H", "Alarm_HH"))
        with self._lock:
            self.db.execute(
                "INSERT INTO hist VALUES(?,?,?,?,?,?,?,?,?,?)",
                (snap["_ts"], snap["_site"], snap["Level_PV"], snap["Pressure_PV"],
                 snap["Inflow"], snap["Outflow"], snap["Valve_MV"],
                 int(snap["Pump_Run"]), int(snap["SIS_Trip"]), alarms))
            self.db.commit()

    def trend(self, site, n=120):
        with self._lock:
            rows = self.db.execute(
                "SELECT ts,level,valve FROM hist WHERE site=? ORDER BY ts DESC LIMIT ?",
                (site, n)).fetchall()
        return rows[::-1]

    def kpis(self):
        with self._lock:
            rows = self.db.execute(
                """SELECT site, AVG(outflow), SUM(sis), SUM(alarms), COUNT(*)
                   FROM hist GROUP BY site""").fetchall()
        out = {}
        for site, avg_out, sis, alarms, n in rows:
            out[site] = {"avg_throughput": round(avg_out or 0, 1),
                         "sis_trips_logged": int(sis or 0),
                         "alarm_samples": int(alarms or 0),
                         "samples": n}
        return out


# --------------------------------------------------------------------------
class SIEMMonitor:
    """L3.2 detection. Rules run against site snapshots + write events."""

    def __init__(self, bus: EventBus, gateway):
        self.bus = bus
        self.gateway = gateway
        self._balance_hist = {}      # site -> deque of (ts, level)
        self._last_seen = {}         # site -> ts (comms)
        self._active = set()         # active (key, condition) for edge-debounce

    def _edge(self, key, cond, source, message, severity):
        """Emit only on transition into the condition."""
        tok = (key, cond)
        if tok not in self._active:
            self._active.add(tok)
            self.bus.emit("SECURITY", source, message, severity=severity)

    def _clear(self, key, cond):
        self._active.discard((key, cond))

    def on_external_write(self, site, tag, value, src):
        sev = "CRITICAL" if tag in ("SIS_Bypass",) else "HIGH"
        self.bus.emit("SECURITY", site,
                      f"Unauthorised write to {tag}={value} (did not pass the OSG)",
                      severity=sev)

    def scan(self, aggregate):
        now = time.time()
        flood = 0
        for key, snap in aggregate.items():
            site = snap["_site"]
            self._last_seen[key] = snap["_ts"]
            self._clear(key, "comms")

            # SIS bypass active (edge)
            if snap.get("SIS_Bypass"):
                self._edge(key, "bypass", site,
                           "SIS BYPASS is ACTIVE - plant trip disabled", "CRITICAL")
            else:
                self._clear(key, "bypass")

            # mass-balance plausibility (spoof / frozen Tx, no peek at truth)
            hist = self._balance_hist.setdefault(key, deque(maxlen=30))
            hist.append((now, snap["Level_PV"]))
            if len(hist) >= 25:
                dlevel = hist[-1][1] - hist[0][1]
                net = snap["Inflow"] - snap["Outflow"]
                if abs(net) > 8 and abs(dlevel) < 0.5:
                    self._edge(key, "spoof", site,
                               "Level transmitter inconsistent with mass balance "
                               "- possible spoof/frozen Tx", "HIGH")
                else:
                    self._clear(key, "spoof")

            flood += int(snap.get("Alarm_HH", False)) + int(snap.get("Alarm_LL", False))

        if flood >= 3:
            self._edge("PLANT", "flood", "PLANT",
                       f"Alarm flood: {flood} critical alarms active", "HIGH")
        else:
            self._clear("PLANT", "flood")

        # comms loss (edge)
        for key, ts in self._last_seen.items():
            if now - ts > 5:
                self._edge(key, "comms", key.split("/")[0],
                           "Comms loss to PLC (no data > 5s)", "HIGH")


# --------------------------------------------------------------------------
class ScenarioEngine:
    """Training layer: timed injects + objectives + scoring."""

    def __init__(self, sites, gateway, bus: EventBus):
        self.sites = sites            # key -> SiteServer
        self.gateway = gateway
        self.bus = bus
        self.active = None
        self.t0 = None
        self._done = set()
        self.score = 0
        self.objectives = []
        self._steps = []
        self._fired = set()

    def _site(self, key):
        return self.sites[key]

    def list_scenarios(self):
        return [{"id": k, "title": v["title"], "desc": v["desc"]}
                for k, v in CATALOG.items()]

    def start(self, scenario_id):
        sc = CATALOG.get(scenario_id)
        if not sc:
            return False
        self.active = scenario_id
        self.t0 = time.time()
        self.score = 0
        self._fired = set()
        self._done = set()
        self.objectives = [dict(o, met=False) for o in sc["objectives"]]
        self._steps = sc["steps"]
        self.bus.emit("TRAINING", "INSTRUCTOR",
                      f"Scenario started: {sc['title']}", severity="INFO")
        return True

    def stop(self):
        if self.active:
            self.bus.emit("TRAINING", "INSTRUCTOR",
                          f"Scenario ended. Score {self.score}/"
                          f"{sum(o['points'] for o in self.objectives)}")
        self.active = None

    def tick(self, aggregate):
        if not self.active:
            return
        t = time.time() - self.t0
        sc = CATALOG[self.active]
        # fire timed injects
        for i, (delay, fn) in enumerate(self._steps):
            if i not in self._fired and t >= delay:
                self._fired.add(i)
                fn(self)
        # evaluate objectives
        for o in self.objectives:
            if not o["met"] and o["check"](self, aggregate, t):
                o["met"] = True
                self.score += o["points"]
                self.bus.emit("TRAINING", "LEARNER",
                              f"Objective met (+{o['points']}): {o['label']}")

    def status(self):
        return {
            "active": self.active,
            "elapsed": round(time.time() - self.t0, 1) if self.t0 else 0,
            "score": self.score,
            "max": sum(o["points"] for o in self.objectives) if self.objectives else 0,
            "objectives": [{"label": o["label"], "met": o["met"],
                            "points": o["points"]} for o in self.objectives],
        }


# ----- inject helpers -----
def _inject_spoof(eng):
    s = next(iter(eng.sites.values()))
    s.unit.lt.spoof_active = True
    s.unit.lt.spoof_value = s.unit.level
    eng.bus.emit("PROCESS", s.unit.site, "[inject] level Tx frozen by attacker")


def _inject_sis_bypass(eng):
    s = next(iter(eng.sites.values()))
    s._vars["SIS_Bypass"].write_value(True)   # external write -> SIEM should catch
    eng.bus.emit("PROCESS", s.unit.site, "[inject] remote SIS bypass attempted")


def _inject_overfill(eng):
    s = next(iter(eng.sites.values()))
    s._vars["Level_SP"].write_value(99.0)      # external unauthorised setpoint
    eng.bus.emit("PROCESS", s.unit.site, "[inject] setpoint pushed to 99% (unauthorised)")


def _inject_pump_trip(eng):
    s = next(iter(eng.sites.values()))
    s.unit.pump_cmd = False
    eng.bus.emit("PROCESS", s.unit.site, "[inject] discharge pump tripped")


# ----- objective checks (eng, aggregate, t) -----
def _first(agg):
    return next(iter(agg.values())) if agg else {}

CATALOG = {
    "proc_upset": {
        "title": "Process upset - discharge pump trip",
        "desc": "Pump trips, level climbs. Trainee must intervene before HH.",
        "steps": [(8, _inject_pump_trip)],
        "objectives": [
            {"label": "Operator took inlet to MANUAL or cut SP before HH",
             "points": 30,
             "check": lambda e, a, t: (not _first(a).get("Mode_Auto", True))
                      or _first(a).get("Level_SP", 100) <= 30},
            {"label": "No SIS trip occurred (stayed below HH)",
             "points": 20,
             "check": lambda e, a, t: t > 40 and not _first(a).get("SIS_Trip", False)},
        ],
    },
    "tx_spoof": {
        "title": "Cyber - level transmitter spoof",
        "desc": "Attacker freezes the level reading while the vessel keeps filling. "
                "SIEM should flag a mass-balance inconsistency.",
        "steps": [(6, _inject_spoof), (8, _inject_overfill)],
        "objectives": [
            {"label": "Spoof/integrity event raised by SIEM",
             "points": 40,
             "check": lambda e, a, t: any("spoof" in ev["message"].lower()
                      for ev in e.bus.recent(80))},
            {"label": "Learner cleared spoof (validated field instrument)",
             "points": 20,
             "check": lambda e, a, t:
                      not next(iter(e.sites.values())).unit.lt.spoof_active},
        ],
    },
    "sis_bypass": {
        "title": "Cyber - remote SIS bypass + overfill",
        "desc": "Attacker disables the plant trip and drives an overfill. "
                "Detect the bypass and restore the safety function fast.",
        "steps": [(5, _inject_sis_bypass), (7, _inject_overfill)],
        "objectives": [
            {"label": "Unauthorised SIS-bypass write detected",
             "points": 40,
             "check": lambda e, a, t: any("BYPASS" in ev["message"].upper()
                      for ev in e.bus.recent(80))},
            {"label": "SIS bypass cleared (safety restored)",
             "points": 30,
             "check": lambda e, a, t: t > 12 and not _first(a).get("SIS_Bypass", True)},
        ],
    },
}
