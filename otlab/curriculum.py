"""
otlab.curriculum  -  guided L0 to L5 training content.

Plain data so it is easy to edit. The console renders it as a click-through
walkthrough with a live window into the running simulation for each level.
Order is bottom-up: start at the physical process (L0), build up to the
business systems (L4/5).

live keys map to a panel the console knows how to draw from /api/state:
  instrument | control | scada | controlroom | siem | dmz | historian
"""

LEVELS = [
    {
        "id": "L0",
        "code": "Level 0",
        "zone": "I&C",
        "title": "Instrumentation and actuation",
        "what": ("The physical layer. Instruments measure the process and final "
                 "elements act on it. There is no logic here - things are only "
                 "sensed and moved. Everything above exists to make sense of this "
                 "layer and act through it."),
        "lives": ["Level / pressure / flow transmitters", "Control valves",
                  "ESD valves", "Pumps and motors", "Temperature sensors"],
        "up": "Raw measurements (4-20 mA, HART, fieldbus) sent up to the PLC.",
        "down": "Valve positions and motor commands driven by the PLC.",
        "live": "instrument",
        "quiz": {
            "q": "What lives at Level 0?",
            "options": ["Field instruments, valves and actuators",
                        "PLCs running the control logic",
                        "Corporate dashboards and reports"],
            "answer": 0,
            "explain": ("Level 0 only senses and actuates. The logic that decides "
                        "what to do lives one level up, at Level 1."),
        },
    },
    {
        "id": "L1",
        "code": "Level 1",
        "zone": "I&C",
        "title": "Basic process control and safety",
        "what": ("The controllers. A PLC or RTU runs the control logic on a fast "
                 "scan - for example a PID loop holding a vessel level at its "
                 "setpoint. A separate Safety Instrumented System trips the plant "
                 "on a dangerous condition (such as high-high level). The SIS is "
                 "kept independent of normal control on purpose."),
        "lives": ["PLCs and RTUs", "Remote IO", "Telemetry / fieldbuses",
                  "Safety Instrumented System (SIS)", "Fire and gas (FGS)"],
        "up": "Process values, modes and alarms sent up to SCADA, often over OPC UA.",
        "down": "Setpoints, mode changes and commands received from SCADA.",
        "live": "control",
        "quiz": {
            "q": "Why keep the SIS separate from normal process control?",
            "options": ["To make the operator screens load faster",
                        "So a control failure cannot also disable safety",
                        "To avoid buying extra hardware"],
            "answer": 1,
            "explain": ("Independence is the whole point: a fault in the basic "
                        "control system must not be able to take out the protective "
                        "trip that keeps the plant safe."),
        },
    },
    {
        "id": "L2",
        "code": "Level 2",
        "zone": "OT",
        "title": "SCADA and supervisory control",
        "what": ("Where operators see and supervise the plant. HMIs show live "
                 "values, raise alarms, and let an operator change a setpoint, "
                 "switch a loop to manual, or start and stop equipment. Level 2 "
                 "talks to the Level 1 controllers over OPC UA and other protocols."),
        "lives": ["SCADA HMIs", "Alarm management", "Remote operations"],
        "up": "Aggregated, displayable data passed up to the control room.",
        "down": "Operator actions (setpoints, modes, start/stop) sent to the PLCs.",
        "live": "scada",
        "quiz": {
            "q": "What is the operator mainly doing at Level 2?",
            "options": ["Writing the PLC control code",
                        "Supervising the plant, adjusting setpoints, handling alarms",
                        "Running the corporate analytics"],
            "answer": 1,
            "explain": ("Level 2 is supervisory. The operator watches the process "
                        "and steers it through setpoints and mode changes; the "
                        "fast control still happens in the PLC at Level 1."),
        },
    },
    {
        "id": "L3.1",
        "code": "Level 3.1",
        "zone": "OT",
        "title": "Centralised and advanced control",
        "what": ("The central control room. A single SCADA screen runs one area; "
                 "Level 3.1 brings many sites and fields together so they can be "
                 "operated as one. This is where the PCC and FCC sit, along with "
                 "advanced control and the wider OT control applications."),
        "lives": ["Process Control Centre (PCC)", "Field Control Centre (FCC)",
                  "Advanced process control", "OT control applications"],
        "up": "A whole-of-field operating picture for the business layers above.",
        "down": "Coordinated operating decisions pushed back down to each site.",
        "live": "controlroom",
        "quiz": {
            "q": "How is the central control room different from a single SCADA screen?",
            "options": ["It only controls one valve",
                        "It operates many sites and fields together",
                        "It is where historical data is stored"],
            "answer": 1,
            "explain": ("Level 3.1 is the wide view: many areas operated centrally, "
                        "with advanced control on top, rather than one HMI for one "
                        "area."),
        },
    },
    {
        "id": "L3.2",
        "code": "Level 3.2",
        "zone": "OT",
        "title": "OT systems management",
        "what": ("Keeping the OT environment healthy and secure. This layer covers "
                 "monitoring, configuration and patch management, virtualisation, "
                 "and security monitoring through a SIEM. It does not run the "
                 "process; it looks after the systems that do."),
        "lives": ["SIEM and security monitoring", "Configuration management",
                  "Patch management", "Virtualisation", "Admin and monitoring"],
        "up": "Health and security signals for site and corporate oversight.",
        "down": "Updates, patches and configuration pushed to OT systems.",
        "live": "siem",
        "quiz": {
            "q": "Which of these belongs to Level 3.2?",
            "options": ["A pressure transmitter",
                        "SIEM, patching and configuration management",
                        "A discharge control valve"],
            "answer": 1,
            "explain": ("Level 3.2 is management and security of the OT systems - "
                        "monitoring, patching, configuration - not the field "
                        "hardware itself."),
        },
    },
    {
        "id": "DMZ",
        "code": "DMZ",
        "zone": "Boundary",
        "title": "The OT / IT boundary",
        "what": ("A demilitarised zone between operations and corporate IT. OT and "
                 "IT never connect directly. Everything crossing between them passes "
                 "through controlled gateways - including the OPC security gateway "
                 "(Kepware OSG) and the historian gateway - so the boundary stays a "
                 "single, monitored, auditable chokepoint."),
        "lives": ["OPC security gateway (Kepware OSG)", "Historian gateway",
                  "Remote access gateway", "Web gateway"],
        "up": "Sanctioned, logged data flowing from OT to IT.",
        "down": "Approved requests flowing from IT back into OT, every one audited.",
        "live": "dmz",
        "quiz": {
            "q": "Why route all OT-to-IT traffic through the DMZ gateways?",
            "options": ["To make the PLCs run faster",
                        "So OT and IT never connect directly - one controlled path",
                        "To avoid having to use OPC"],
            "answer": 1,
            "explain": ("The DMZ removes any direct path between OT and IT. One "
                        "controlled, monitored gateway is far easier to defend and "
                        "audit than many direct links."),
        },
    },
    {
        "id": "L45",
        "code": "Level 4 / 5",
        "zone": "IS",
        "title": "Business and information systems",
        "what": ("The corporate layer. Historians such as IP21 keep long-term "
                 "process data; analytics and optimisation tools (Spotfire, XECTA, "
                 "P2 Apollo) and business systems (CMMS) use it to plan, report and "
                 "improve. Engineers and the business analyse here - but they do not "
                 "command the plant from here."),
        "lives": ["Corporate historian (IP21)", "Spotfire", "XECTA", "P2 Apollo",
                  "CMMS", "Corporate applications"],
        "up": "Insight, KPIs and decisions for the business.",
        "down": "Read-only relative to control - no direct commands to the plant.",
        "live": "historian",
        "quiz": {
            "q": "Can Level 4/5 systems directly command a plant valve?",
            "options": ["Yes, the historian writes straight to valves",
                        "No - they analyse data; control stays down in OT"],
            "answer": 1,
            "explain": ("Business systems consume data and produce insight. Any "
                        "command to the plant goes back down through the OT layers "
                        "and the DMZ, never straight from a corporate app."),
        },
    },
]
