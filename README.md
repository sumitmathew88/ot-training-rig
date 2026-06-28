# Santos-style OT Training Rig (Purdue model simulator)

A runnable, attackable simulation of an AU upstream OT stack, built to the
Purdue reference model. It is a training and engineering sandbox: real OPC UA
endpoints at Level 1, a DMZ security gateway, a SIEM, a historian, and a
scenario engine that injects process upsets and cyber attacks for operators
and engineers to detect and respond to.

No real plant is connected. Everything here is simulated.

## How it maps to your Purdue diagram

| Your layer | Real systems | Simulated by |
|---|---|---|
| L4/5 Information Systems | IP21, Spotfire, XECTA, P2 Apollo | `Historian` (SQLite time-series) + KPI view |
| DMZ | Web/Remote/Historian gateways, Kepware OSG | `Gateway` (OPC aggregation, write allow-list, audit ledger) |
| L3.2 Management | SIEM, config, monitoring, patch | `SIEMMonitor` (rule-based OT detection) |
| L3.1 Centralised Control | Central Control Room (PCC/FCC) | Console "Control Room" aggregated view |
| L2 SCADA | Remote operations | Web console (OPC client lives in the platform, not the browser) |
| L1 BPCS / Plant Trip / SIS-FGS | PLCs, RTUs, telemetry | `SiteServer` per skid = real OPC UA server + BPCS PID + independent SIS |
| L0 Instrumentation | Field instruments, valves | `FieldUnit` process model + `Transmitter` (spoofable) |

Three sites ship by default, loosely mirroring your assets: COOPER (V-101),
ROMA-CSG (V-201), PNG-HIDES (V-301). Each is a separator vessel with inlet
control valve, level, pressure, and discharge pump.

## Architecture

```
 Browser (HMI)
     |  HTTP
 [ Console / Control Room ]  L2 / L3.1
     |  in-process
 [ SIEM ] [ Historian ]      L3.2 / L4-5
     |
 [ OSG Gateway ]             DMZ   <-- only sanctioned write path + audit
     |  in-process aggregation; OPC UA endpoints stay open
 [ SiteServer COOPER ]  opc.tcp://*:4841   L1 (real OPC UA server)
 [ SiteServer ROMA   ]  opc.tcp://*:4842   L1
 [ SiteServer PNG    ]  opc.tcp://*:4843   L1
     |
 [ FieldUnit + Transmitters ]                L0 process + instruments
```

The Level 1 endpoints are genuine OPC UA servers. Your real SCADA, UAExpert,
or an attacker's OPC client can connect to them directly. That direct path is
the training attack surface: a write that reaches a PLC without passing the
OSG gateway is flagged by the SIEM as unsanctioned.

## Run it

```
pip install -r requirements.txt
python3 run_platform.py
# open http://localhost:8800
```

You will see three site cards (level tanks, valve, pump, mode), a SIEM event
feed, a historian KPI tab, and a Training tab with scenarios.

To connect an external OPC UA client (e.g. UAExpert) for engineering or red-team
practice:
```
opc.tcp://<host>:4841/otlab/COOPER/V-101/
```

## Training scenarios (shipped)

1. Process upset - discharge pump trip. Level climbs after a pump trip;
   the trainee must take the loop to MANUAL or cut the setpoint before the SIS
   trips on High-High.
2. Cyber - level transmitter spoof. The reading is frozen while the vessel
   keeps filling. The SIEM raises a mass-balance inconsistency (it does not
   peek at the true value). Trainee validates the field instrument to clear it.
3. Cyber - remote SIS bypass + overfill. The plant trip is disabled and an
   overfill is driven. Trainee must detect the bypass and restore the safety
   function.

Each scenario has objectives and a score. The instructor starts a scenario
from the Training tab; the learner responds from the Control Room tab.

## Why writes can still succeed

The SIS bypass and unauthorised setpoint actually take effect on the process.
That is deliberate. OT security training is about detection and timely
response, not pretending a determined actor on the OT LAN cannot write to a
PLC. The score rewards how fast and how correctly the learner reacts.

## Extend it

The code is small and modular on purpose:

- `otlab/field.py` - add unit types (wellhead/plunger, compressor, FGS), more
  instruments, second-order dynamics.
- `otlab/site.py` - add tags, alarms, or a Modbus/DNP3 server alongside OPC UA.
- `otlab/gateway.py` - tighten the write allow-list, add per-user auth, MFA,
  rate limits, or a deny-and-quarantine response.
- `otlab/platform.py` - add SIEM rules (setpoint ramp-rate limits, out-of-hours
  writes, new-source detection), more historian KPIs, and new scenarios in
  `CATALOG`.
- `otlab/console.py` - trends, an alarm summary, an instructor cyber-inject panel.

## Roadmap to a production-grade lab

Phase 2
- Real connectors: point the historian at IP21, the gateway at an actual
  Kepware OSG, and add a Citect/Experion HMI as a second L2 client.
- Protocol breadth: Modbus TCP and DNP3 outstations per site; a soft-PLC
  (OpenPLC) running IEC 61131-3 logic as an alternative L1.
- SIS depth: separate SIS logic solver with voting (2oo3), proof-test tracking.

Phase 3
- Network realism: run each layer in its own container/VLAN with a firewalled
  DMZ, so packet capture and segmentation testing become possible.
- Multi-user training: instructor console, multiple learner seats, session
  recording, after-action review against the event timeline.
- Scenario library mapped to AESCSF / IEC 62443 controls and to your CIRMP
  cyber risk rows, so each exercise traces to a control you report on.

## Files

```
otlab/field.py      L0 process + L1 BPCS/SIS
otlab/site.py       L1 OPC UA server + write-provenance detection
otlab/gateway.py    DMZ OSG: aggregation, write policy, audit ledger
otlab/platform.py   EventBus, Historian, SIEM, ScenarioEngine
otlab/console.py    Web training console (Flask)
run_platform.py     launcher
```
