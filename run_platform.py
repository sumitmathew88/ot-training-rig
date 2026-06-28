"""
run_platform.py  -  OT training rig entrypoint.

Local:       python3 run_platform.py
Production:  gunicorn -c gunicorn.conf.py run_platform:app   (MUST be 1 worker)

Why one worker: each worker would start its own set of OPC UA servers on the
same ports and its own diverging simulation. The platform is a single stateful
process by design. Scale users with threads, not workers.

Environment:
  PORT             web port (default 8800; most hosts set this for you)
  OTLAB_OPC_BIND   address the L1 OPC UA servers bind to (default 127.0.0.1,
                   i.e. NOT exposed). Set 0.0.0.0 only on a private VM where
                   you want external OPC clients (UAExpert) to connect.
  OTLAB_SECRET     Flask session key (set a long random value in production)
  OTLAB_USERS      JSON {username: password_hash} - see make_user.py
"""

import os
import threading
import time

from otlab.field import FieldUnit
from otlab.site import SiteServer
from otlab.gateway import Gateway
from otlab.platform import EventBus, Historian, SIEMMonitor, ScenarioEngine
from otlab.console import make_app
from otlab.auth import install_auth

SITE_DEFS = [
    ("V-101", "COOPER",    4841, 600.0),
    ("V-201", "ROMA-CSG",  4842, 520.0),
    ("V-301", "PNG-HIDES", 4843, 680.0),
]

OPC_BIND = os.environ.get("OTLAB_OPC_BIND", "127.0.0.1")


def build():
    bus = EventBus()
    gw = Gateway(bus)
    siem = SIEMMonitor(bus, gw)
    hist = Historian(os.environ.get("OTLAB_DB", "otlab_history.db"))

    sites = {}
    for tag, site, port, up in SITE_DEFS:
        unit = FieldUnit(tag=tag, site=site)
        unit.upstream_p = up
        srv = SiteServer(unit, port, on_external_write=siem.on_external_write,
                         bind=OPC_BIND)
        srv.start()
        sites[f"{site}/{tag}"] = srv
        gw.register(srv)
        print(f"[L1] {site}/{tag} OPC UA up on {srv.endpoint}")

    eng = ScenarioEngine(sites, gw, bus)
    return bus, gw, siem, hist, sites, eng


def supervisory_loop(gw, siem, hist, eng, stop):
    while not stop.is_set():
        agg = gw.aggregate()
        siem.scan(agg)
        for snap in agg.values():
            hist.record(snap)
        eng.tick(agg)
        time.sleep(1.0)


# ---- start the platform exactly once, at import ----
_STARTED = False
app = None


def _boot():
    global app, _STARTED
    if _STARTED:
        return app
    _STARTED = True
    bus, gw, siem, hist, sites, eng = build()
    stop = threading.Event()
    threading.Thread(target=supervisory_loop,
                     args=(gw, siem, hist, eng, stop), daemon=True).start()
    bus.emit("TRAINING", "PLATFORM", "OT training rig online", "INFO")
    a = make_app(bus, gw, siem, hist, sites, eng)
    install_auth(a)          # credential gate in front of everything
    app = a
    return app


app = _boot()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8800))
    print(f"[L2] training console -> http://localhost:{port}  (login required)")
    app.run(host="0.0.0.0", port=port, threaded=True)
