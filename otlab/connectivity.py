"""
otlab.connectivity  -  OPC UA and layer connectivity trainer.

Configure how each tier connects over OPC UA:

  L1 PLC      OPC UA server  (the controller exposes its tags)
  L2 SCADA    OPC UA client  (subscribes to the PLC server)
  DMZ OSG     gateway        (Kepware: channel/device south, OPC UA server north)
  L5 IP21     OPC UA client  (collects from the OSG northbound server)

Field-level mistakes (bad endpoint, missing value) are hard errors and block
the save. Best-practice deviations (security policy that does not match the
peer, read/write left open to IT) come back as advisory notes - the teaching
points - but still save, so a learner can see the consequence.
"""

import re

SEC_POLICIES = ["None", "Basic256Sha256"]
SEC_MODES = ["None", "Sign", "SignAndEncrypt"]

LAYERS = [
    {
        "id": "PLC", "label": "Level 1 - PLC", "role": "OPC UA server",
        "intro": "The controller exposes its I/O as an OPC UA server. SCADA and "
                 "the gateway connect to this endpoint.",
        "fields": [
            {"k": "platform", "label": "Controller platform", "type": "select",
             "options": ["Allen-Bradley ControlLogix", "Emerson DeltaV",
                         "Yokogawa CENTUM", "Schneider M580", "Siemens S7-1500"],
             "default": "Emerson DeltaV",
             "help": "The controller hardware running the basic process control."},
            {"k": "endpoint", "label": "OPC UA server endpoint", "type": "text",
             "default": "opc.tcp://plc-wellpad1:4840/ua/plc",
             "help": "The address the PLC's OPC UA server listens on."},
            {"k": "sec_policy", "label": "Security policy", "type": "select",
             "options": SEC_POLICIES, "default": "Basic256Sha256",
             "help": "Encryption suite. Clients must use the same policy to connect."},
            {"k": "sec_mode", "label": "Security mode", "type": "select",
             "options": SEC_MODES, "default": "SignAndEncrypt",
             "help": "None, Sign (integrity) or Sign and encrypt (integrity + privacy)."},
            {"k": "auth", "label": "Authentication", "type": "select",
             "options": ["Anonymous", "Username/Password", "Certificate"],
             "default": "Username/Password",
             "help": "How connecting clients prove who they are."},
            {"k": "scan_ms", "label": "Scan rate (ms)", "type": "number",
             "default": 250,
             "help": "How often the controller refreshes its OPC values."},
        ],
    },
    {
        "id": "SCADA", "label": "Level 2 - SCADA", "role": "OPC UA client",
        "intro": "SCADA is an OPC UA client. It connects to the PLC server and "
                 "subscribes to the tags it needs to display and alarm.",
        "fields": [
            {"k": "platform", "label": "SCADA platform", "type": "select",
             "options": ["AVEVA Plant SCADA (Citect)", "GE iFIX",
                         "Honeywell Experion", "Inductive Ignition"],
             "default": "AVEVA Plant SCADA (Citect)",
             "help": "The supervisory HMI software."},
            {"k": "connect_endpoint", "label": "Connect to PLC endpoint", "type": "text",
             "default": "opc.tcp://plc-wellpad1:4840/ua/plc",
             "help": "The PLC OPC UA server this SCADA subscribes to. Match the L1 endpoint."},
            {"k": "sec_policy", "label": "Security policy", "type": "select",
             "options": SEC_POLICIES, "default": "Basic256Sha256",
             "help": "Must match the PLC server's policy or the session is refused."},
            {"k": "publish_ms", "label": "Publishing interval (ms)", "type": "number",
             "default": 1000,
             "help": "How often the subscription sends a batch of changes to SCADA."},
            {"k": "sampling_ms", "label": "Sampling interval (ms)", "type": "number",
             "default": 500,
             "help": "How often each item is checked for change on the server."},
            {"k": "deadband", "label": "Analog deadband (% of range)", "type": "number",
             "default": 1,
             "help": "Ignore analog changes smaller than this, to cut chatter."},
        ],
    },
    {
        "id": "OSG", "label": "DMZ - Kepware OSG", "role": "OPC security gateway",
        "intro": "The OPC security gateway. It connects south to the PLC through a "
                 "channel and device, and re-serves a curated namespace north to IT "
                 "as its own OPC UA server. The single audited crossing point.",
        "fields": [
            {"k": "channel", "label": "Channel name", "type": "text",
             "default": "Wellpad1_OPCUA",
             "help": "A Kepware channel groups a connection and its protocol driver."},
            {"k": "driver", "label": "Channel driver (south)", "type": "select",
             "options": ["OPC UA Client", "Modbus TCP/IP", "EtherNet/IP", "DNP3"],
             "default": "OPC UA Client",
             "help": "How the gateway talks to the PLC below it."},
            {"k": "device", "label": "Device name", "type": "text",
             "default": "V101_PLC",
             "help": "The specific controller under the channel. Tags sit under it."},
            {"k": "north_endpoint", "label": "Northbound OPC UA server", "type": "text",
             "default": "opc.tcp://osg-dmz:49320",
             "help": "The gateway's own server endpoint, facing IT / Level 5."},
            {"k": "north_sec", "label": "Northbound security policy", "type": "select",
             "options": SEC_POLICIES, "default": "Basic256Sha256",
             "help": "Security for IT clients. Keep it signed and encrypted."},
            {"k": "allowed_clients", "label": "Allowed IT clients", "type": "text",
             "default": "IP21",
             "help": "Which IT systems may connect northbound. Everything else is denied."},
            {"k": "read_only", "label": "Enforce read-only for IT", "type": "toggle",
             "default": True,
             "help": "Stop IT systems writing to the plant. Strongly recommended on."},
        ],
    },
    {
        "id": "IP21", "label": "Level 5 - IP21", "role": "OPC UA client",
        "intro": "AspenTech IP21 collects the published tags from the OSG northbound "
                 "server into the production / corporate historian.",
        "fields": [
            {"k": "product", "label": "Historian", "type": "select",
             "options": ["AspenTech IP21", "PI System", "Canary"],
             "default": "AspenTech IP21",
             "help": "The corporate / production historian."},
            {"k": "connect_endpoint", "label": "Collect from OSG endpoint", "type": "text",
             "default": "opc.tcp://osg-dmz:49320",
             "help": "The OSG northbound server IP21 reads from. Match the OSG north endpoint."},
            {"k": "sec_policy", "label": "Security policy", "type": "select",
             "options": SEC_POLICIES, "default": "Basic256Sha256",
             "help": "Must match the OSG northbound policy."},
            {"k": "collection_ms", "label": "Collection rate (ms)", "type": "number",
             "default": 5000,
             "help": "How often IP21 collects each tag value."},
            {"k": "compression", "label": "Historian compression", "type": "toggle",
             "default": True,
             "help": "Store only meaningful changes, to reduce storage."},
        ],
    },
]

_SPEC = {l["id"]: l for l in LAYERS}


class ConfigStore:
    def __init__(self, store):
        self.store = store

    def meta(self):
        return LAYERS

    def _full(self, user):
        cfg = {l["id"]: {f["k"]: f["default"] for f in l["fields"]} for l in LAYERS}
        for layer, vals in self.store.load_conn(user).items():
            if layer in cfg:
                cfg[layer].update(vals)
        return cfg

    def get(self, user):
        return self._full(user)

    def osg(self, user):
        c = self._full(user)["OSG"]
        return {"channel": c["channel"], "device": c["device"]}

    def set(self, user, layer, payload):
        spec = _SPEC.get(layer)
        if not spec:
            return False, ["Unknown layer."], []
        errors, clean = [], {}
        for f in spec["fields"]:
            v = payload.get(f["k"])
            if f["type"] == "number":
                try:
                    v = int(v)
                    if v <= 0:
                        errors.append(f"{f['label']} must be a positive number.")
                except (TypeError, ValueError):
                    errors.append(f"{f['label']} must be a number.")
                    v = f["default"]
            elif f["type"] == "toggle":
                v = bool(v)
            elif f["type"] == "select":
                if v not in f["options"]:
                    errors.append(f"{f['label']}: choose a valid option.")
                    v = f["default"]
            else:
                v = (v or "").strip()
                if not v:
                    errors.append(f"{f['label']} is required.")
                if "endpoint" in f["k"] and v and not v.startswith("opc.tcp://"):
                    errors.append(f"{f['label']} should be an opc.tcp:// address.")
            clean[f["k"]] = v
        if errors:
            return False, errors, []
        self.store.save_conn(user, layer, clean)
        return True, [], self._notes(self._full(user))

    def _notes(self, c):
        n = []
        if c["SCADA"]["sec_policy"] != c["PLC"]["sec_policy"]:
            n.append("SCADA security policy does not match the PLC - the OPC UA "
                     "session would be refused until they match.")
        if c["SCADA"]["connect_endpoint"] != c["PLC"]["endpoint"]:
            n.append("SCADA is pointed at a different endpoint than the PLC server.")
        if c["IP21"]["sec_policy"] != c["OSG"]["north_sec"]:
            n.append("IP21 security policy does not match the OSG northbound policy.")
        if c["IP21"]["connect_endpoint"] != c["OSG"]["north_endpoint"]:
            n.append("IP21 is collecting from a different endpoint than the OSG serves.")
        if c["OSG"]["north_endpoint"] == c["PLC"]["endpoint"]:
            n.append("The OSG northbound endpoint is the same as the PLC - they should "
                     "be separate hosts on opposite sides of the DMZ.")
        if not c["OSG"]["read_only"]:
            n.append("Read-only is OFF at the OSG - IT systems could write to the "
                     "plant. Turn it on unless you have a specific reason.")
        return n

    def topology(self, user):
        c = self._full(user)
        return [
            {"id": "PLC", "label": "PLC (L1)", "role": "OPC UA server",
             "detail": c["PLC"]["endpoint"], "sec": c["PLC"]["sec_policy"]},
            {"id": "SCADA", "label": "SCADA (L2)", "role": "client \u2192 PLC",
             "detail": c["SCADA"]["connect_endpoint"], "sec": c["SCADA"]["sec_policy"]},
            {"id": "OSG", "label": "Kepware OSG (DMZ)", "role": "gateway",
             "detail": f"{c['OSG']['channel']}.{c['OSG']['device']} \u2192 server {c['OSG']['north_endpoint']}",
             "sec": c["OSG"]["north_sec"]},
            {"id": "IP21", "label": "IP21 (L5)", "role": "client \u2192 OSG",
             "detail": c["IP21"]["connect_endpoint"], "sec": c["IP21"]["sec_policy"]},
        ]
