"""
otlab.gateway  -  DMZ / Kepware OSG (OPC Security Gateway).

In the real stack this is the broker that sits in the DMZ and is the ONLY
sanctioned path between the OT control layers (L1/L2) and everything above
(L3 control room, L4/5 corporate). Here it:

  * aggregates the latest tag set from every site (northbound),
  * enforces a write allow-list + role check on anything going south,
  * keeps an audit ledger of every sanctioned write (who/what/when).

Anything that changes a PLC without a matching ledger entry was NOT brokered
here - that is the signal the SIEM keys on.
"""

import time

# Tags an upstream operator/control-room user is permitted to write.
WRITE_ALLOWLIST = {"Level_SP", "Mode_Auto", "Valve_Manual", "Pump_Cmd", "Reset_Cmd"}
# SIS_Bypass is deliberately NOT brokerable from above - it is a local
# maintenance function. Anyone setting it remotely is suspicious by design.

ROLE_RIGHTS = {
    "OPERATOR": {"Level_SP", "Mode_Auto", "Valve_Manual", "Pump_Cmd", "Reset_Cmd"},
    "ENGINEER": WRITE_ALLOWLIST,
    "READONLY": set(),
}


class Gateway:
    def __init__(self, event_bus):
        self.sites = {}            # name -> SiteServer
        self.ledger = []           # sanctioned writes
        self.bus = event_bus

    def register(self, site_server):
        self.sites[site_server.unit.site + "/" + site_server.unit.tag] = site_server

    # northbound
    def aggregate(self):
        return {k: dict(s.latest) for k, s in self.sites.items() if s.latest}

    # southbound (policy enforced)
    def write(self, site_key, tag, value, user="OPERATOR", role="OPERATOR"):
        site = self.sites.get(site_key)
        if site is None:
            return False, "unknown site"
        if tag not in WRITE_ALLOWLIST:
            self.bus.emit("SECURITY", site_key,
                          f"Gateway BLOCKED write to non-brokerable tag {tag} by {user}")
            return False, "tag not brokerable"
        if tag not in ROLE_RIGHTS.get(role, set()):
            self.bus.emit("SECURITY", site_key,
                          f"Gateway BLOCKED {tag} - role {role} lacks rights")
            return False, "insufficient role"
        site.command(tag, value, source=f"{role}:{user}")
        self.ledger.append({"ts": time.time(), "site": site_key, "tag": tag,
                            "value": value, "user": user, "role": role})
        return True, "ok"
