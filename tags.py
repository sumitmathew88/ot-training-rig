"""
otlab.tags  -  hands-on tag configuration trainer.

A beginner defines a tag the way it is really done on a controller, then walks
it up the Purdue stack:

  PLC (L1)  ->  SCADA (L2)  ->  Kepware OSG (DMZ)  ->  IP21 (L5)

Each tag carries realistic engineering config (category, data type, unit,
range, alarms, history). Validation enforces the rules a beginner needs to
learn: digital points are Boolean with no unit, analog points need a range and
ordered alarm setpoints, history needs a sample rate, and so on.

The lifecycle assigns real artefacts as the tag advances: an OPC item path when
it is published through the OSG, and an IP21 historian tag name at L5.
"""

import re
import time

CATEGORIES = {
    "AI": "Analog input",
    "AO": "Analog output / setpoint",
    "DI": "Digital input / status",
    "DO": "Digital output / command",
}
DATATYPES = ["Real", "Integer", "Boolean"]
UNITS = ["none", "DegC", "kPa", "barg", "%", "m3/h", "mm", "kW", "rpm"]
SAMPLES = ["1 s", "5 s", "10 s", "1 min", "5 min"]
DIGITAL_STATES = ["Closed", "Open", "Stopped", "Running", "Activated", "Faulted"]

# Four lifecycle stages, matching the layers the tag crosses.
STAGES = ["PLC", "SCADA", "OSG", "IP21"]
STAGE_LABEL = {
    "PLC": "Defined on PLC (L1)",
    "SCADA": "Configured in SCADA (L2)",
    "OSG": "Published via Kepware OSG (DMZ)",
    "IP21": "Historised in IP21 (L5)",
}
ADVANCE_LABEL = {
    0: "Configure in SCADA",
    1: "Publish via Kepware OSG",
    2: "Historise in IP21",
}

TEMPLATES = [
    {"label": "Temperature (AI)", "name": "TI-101",
     "description": "Separator inlet temperature", "category": "AI",
     "datatype": "Real", "unit": "DegC", "range_min": 0, "range_max": 150,
     "alarm_enabled": True, "sp_H": 90, "sp_HH": 110,
     "history_enabled": True, "sample": "5 s"},
    {"label": "Pressure (AI)", "name": "PT-102",
     "description": "Separator pressure", "category": "AI",
     "datatype": "Real", "unit": "kPa", "range_min": 0, "range_max": 1000,
     "alarm_enabled": True, "sp_H": 800, "sp_HH": 950,
     "history_enabled": True, "sample": "5 s"},
    {"label": "Level setpoint (AO)", "name": "LIC-103-SP",
     "description": "Level controller setpoint", "category": "AO",
     "datatype": "Real", "unit": "%", "range_min": 0, "range_max": 100,
     "alarm_enabled": False, "history_enabled": True, "sample": "10 s"},
    {"label": "Valve position (DI)", "name": "XV-201-ZSC",
     "description": "Inlet valve closed feedback", "category": "DI",
     "datatype": "Boolean", "unit": "none", "alarm_enabled": True,
     "alarm_state": "Closed", "history_enabled": True, "sample": "1 s"},
    {"label": "Pump status (DI)", "name": "P-301-RUN",
     "description": "Discharge pump running status", "category": "DI",
     "datatype": "Boolean", "unit": "none", "alarm_enabled": True,
     "alarm_state": "Stopped", "history_enabled": True, "sample": "1 s"},
    {"label": "ESD command (DO)", "name": "ESD-901",
     "description": "Emergency shutdown command", "category": "DO",
     "datatype": "Boolean", "unit": "none", "alarm_enabled": True,
     "alarm_state": "Activated", "history_enabled": True, "sample": "1 s"},
    {"label": "Valve open command (DO)", "name": "XV-201-OPEN",
     "description": "Inlet valve open command", "category": "DO",
     "datatype": "Boolean", "unit": "none", "alarm_enabled": False,
     "history_enabled": True, "sample": "1 s"},
]


def validate(p):
    """Return a list of human-readable errors (empty list = valid)."""
    e = []
    name = (p.get("name") or "").strip()
    if not name:
        e.append("Tag name is required.")
    elif not re.match(r"^[A-Za-z0-9_-]{2,30}$", name):
        e.append("Tag name must be 2-30 characters: letters, numbers, - or _ only.")

    cat = p.get("category")
    if cat not in CATEGORIES:
        e.append("Choose a tag category (AI, AO, DI or DO).")
    dt = p.get("datatype")
    if dt not in DATATYPES:
        e.append("Choose a data type.")

    analog = cat in ("AI", "AO")
    digital = cat in ("DI", "DO")
    if digital and dt != "Boolean":
        e.append("Digital tags (DI/DO) must be Boolean.")
    if analog and dt == "Boolean":
        e.append("Analog tags (AI/AO) must be Real or Integer, not Boolean.")

    unit = p.get("unit") or "none"
    if dt == "Boolean" and unit != "none":
        e.append("Boolean tags have no engineering unit - set unit to none.")
    if analog and unit == "none":
        e.append("Analog tags need an engineering unit (for example DegC, kPa or %).")

    rmin = rmax = None
    if analog:
        try:
            rmin = float(p.get("range_min"))
            rmax = float(p.get("range_max"))
            if rmin >= rmax:
                e.append("Range minimum must be less than maximum.")
        except (TypeError, ValueError):
            e.append("Analog tags need a numeric range (min and max).")

    alarm = bool(p.get("alarm_enabled"))
    if alarm and analog:
        sps = {}
        for k in ("sp_LL", "sp_L", "sp_H", "sp_HH"):
            v = p.get(k)
            if v not in (None, ""):
                try:
                    sps[k] = float(v)
                except (TypeError, ValueError):
                    e.append(f"Alarm setpoint {k[3:]} must be a number.")
        if not sps:
            e.append("Enable at least one alarm setpoint (LL, L, H or HH), or turn alarms off.")
        seq = [sps[k] for k in ("sp_LL", "sp_L", "sp_H", "sp_HH") if k in sps]
        if seq != sorted(seq):
            e.append("Alarm setpoints must increase in order: LL < L < H < HH.")
        if rmin is not None and rmax is not None:
            for k, v in sps.items():
                if v < rmin or v > rmax:
                    e.append(f"Setpoint {k[3:]} ({v}) is outside the tag range.")
    if alarm and digital and not p.get("alarm_state"):
        e.append("Choose which state raises the alarm (for example Closed).")

    if bool(p.get("history_enabled")) and not p.get("sample"):
        e.append("Choose a history sample rate.")
    return e


class TagRegistry:
    def __init__(self):
        self._tags = {}
        self._seq = 0

    def meta(self):
        return {"categories": CATEGORIES, "datatypes": DATATYPES, "units": UNITS,
                "samples": SAMPLES, "digital_states": DIGITAL_STATES,
                "stages": STAGES, "stage_label": STAGE_LABEL,
                "advance_label": ADVANCE_LABEL, "templates": TEMPLATES}

    def list(self):
        return list(self._tags.values())

    def create(self, p):
        errors = validate(p)
        if errors:
            return None, errors
        self._seq += 1
        tid = f"tag{self._seq}"
        analog = p["category"] in ("AI", "AO")
        tag = {
            "id": tid,
            "name": p["name"].strip(),
            "description": (p.get("description") or "").strip(),
            "category": p["category"],
            "category_label": CATEGORIES[p["category"]],
            "datatype": p["datatype"],
            "unit": p.get("unit") or "none",
            "range_min": float(p["range_min"]) if analog else None,
            "range_max": float(p["range_max"]) if analog else None,
            "alarm_enabled": bool(p.get("alarm_enabled")),
            "sp_LL": _num(p.get("sp_LL")), "sp_L": _num(p.get("sp_L")),
            "sp_H": _num(p.get("sp_H")), "sp_HH": _num(p.get("sp_HH")),
            "alarm_state": p.get("alarm_state") if not analog else None,
            "history_enabled": bool(p.get("history_enabled")),
            "sample": p.get("sample") if p.get("history_enabled") else None,
            "stage": 0,
            "opc_item": "",
            "access": "",
            "ip21_tag": "",
            "ts": time.time(),
        }
        self._tags[tid] = tag
        return tag, []

    def advance(self, tid):
        t = self._tags.get(tid)
        if not t:
            return None
        t["stage"] = min(t["stage"] + 1, len(STAGES) - 1)
        if t["stage"] >= 2 and not t["opc_item"]:
            safe = t["name"].replace("-", "_")
            t["opc_item"] = f"OSG.WELLPAD1.{safe}"
            t["access"] = "Read/Write" if t["category"] in ("AO", "DO") else "Read only"
        if t["stage"] >= 3 and not t["ip21_tag"]:
            t["ip21_tag"] = f"IP21.{t['name'].replace('-', '_')}"
        return t

    def delete(self, tid):
        return self._tags.pop(tid, None) is not None


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
