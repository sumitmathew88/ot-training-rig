"""
otlab.site  -  Purdue Level 1 endpoint exposed over OPC UA.

A SiteServer wraps one FieldUnit and runs a real OPC UA server (one TCP
endpoint per site, exactly like an individual PLC/RTU). The cyclic scan:
  * runs the BPCS/SIS logic,
  * publishes process tags,
  * detects EXTERNAL writes to the OPC address space.

Write provenance
----------------
Sanctioned control (operator via the console, or the DMZ gateway) calls
`command(tag, value, source)`. That records the value as "expected".
If the scan finds a writable tag whose OPC value differs from what was
last commanded, something wrote straight into the PLC's OPC space without
going through the gateway - i.e. an actor on the OT LAN. That fires an
`on_external_write` callback, which the SIEM turns into a security event.
The write still takes effect (the attack succeeds on the process), which is
the point: you train people to DETECT and RESPOND, not to rely on it being
impossible.
"""

import threading
import time

from asyncua.sync import Server

from .field import FieldUnit


class SiteServer:
    def __init__(self, unit: FieldUnit, port: int, scan_hz: float = 10.0,
                 on_external_write=None, bind: str = "127.0.0.1"):
        self.unit = unit
        self.port = port
        self.dt = 1.0 / scan_hz
        self.on_external_write = on_external_write   # (site, tag, value, src)
        self.endpoint = f"opc.tcp://{bind}:{port}/otlab/{unit.site}/{unit.tag}/"
        self.commanded = {}      # sanctioned expected values
        self.latest = {}         # last published snapshot (for historian/SIEM)
        self._vars = {}
        self._server = None
        self._stop = threading.Event()
        self._thread = None

    # ---- sanctioned control path ----
    def command(self, tag, value, source="OPERATOR"):
        self.commanded[tag] = value
        self.unit.apply_write(tag, value)
        if tag in self._vars:
            self._vars[tag].write_value(_coerce(self._vars[tag], value))

    def start(self):
        self._server = Server()
        self._server.set_endpoint(self.endpoint)
        self._server.set_server_name(f"{self.unit.site}/{self.unit.tag} PLC")
        idx = self._server.register_namespace(f"otlab/{self.unit.site}")
        obj = self._server.nodes.objects.add_object(idx, self.unit.tag)

        snap = self.unit.snapshot(self.unit.level)
        for name, val in snap.items():
            v = obj.add_variable(idx, name, val)
            if name in FieldUnit.WRITABLE:
                v.set_writable()
                self.commanded[name] = val
            self._vars[name] = v
        # Reset command (writable, momentary)
        rv = obj.add_variable(idx, "Reset_Cmd", False)
        rv.set_writable()
        self._vars["Reset_Cmd"] = rv
        self.commanded["Reset_Cmd"] = False

        self._server.start()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self):
        while not self._stop.is_set():
            # 1. detect external writes to writable tags
            for tag in list(FieldUnit.WRITABLE) + ["Reset_Cmd"]:
                node = self._vars.get(tag)
                if node is None:
                    continue
                opc_val = node.read_value()
                if tag not in self.commanded:
                    self.commanded[tag] = opc_val
                    continue
                if opc_val != self.commanded[tag]:
                    # external write - unsanctioned
                    self.commanded[tag] = opc_val
                    self.unit.apply_write(tag, opc_val)
                    if self.on_external_write:
                        self.on_external_write(self.unit.site, tag, opc_val, "UNKNOWN")

            # 2. run control + physics
            lvl_meas = self.unit.scan()

            # 3. publish
            snap = self.unit.snapshot(lvl_meas)
            for name, val in snap.items():
                if name in self._vars:
                    self._vars[name].write_value(val)
            snap["_site"] = self.unit.site
            snap["_tag"] = self.unit.tag
            snap["_ts"] = time.time()
            self.latest = snap

            time.sleep(self.dt)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        if self._server:
            self._server.stop()


def _coerce(node, value):
    cur = node.read_value()
    if isinstance(cur, bool):
        return bool(value)
    if isinstance(cur, float):
        return float(value)
    if isinstance(cur, int):
        return int(value)
    return value
