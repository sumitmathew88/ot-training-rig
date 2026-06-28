"""
otlab.console  -  web training platform.

Front door is a guided Level 0 to Level 5 walkthrough (the "Learn" view) with a
live window into the running simulation at each layer and a knowledge check.
The operational views (control room, SIEM, historian, scenarios) sit behind it.
"""

from flask import Flask, jsonify, request

from .curriculum import LEVELS


def make_app(bus, gateway, siem, historian, sites, engine):
    app = Flask(__name__)

    @app.get("/")
    def index():
        return HTML

    @app.get("/api/curriculum")
    def curriculum():
        return jsonify(LEVELS)

    @app.get("/api/state")
    def state():
        agg = gateway.aggregate()
        for key, srv in sites.items():
            if key in agg:
                agg[key]["_spoof"] = srv.unit.lt.spoof_active
        return jsonify({
            "sites": agg,
            "events": bus.recent(40),
            "kpis": historian.kpis(),
            "scenarios": engine.list_scenarios(),
            "scenario_status": engine.status(),
            "ledger": gateway.ledger[-12:][::-1],
        })

    @app.post("/api/command")
    def command():
        b = request.get_json(force=True)
        ok, msg = gateway.write(b["site"], b["tag"], b["value"],
                                user=b.get("user", "trainee"),
                                role=b.get("role", "OPERATOR"))
        return jsonify({"ok": ok, "msg": msg})

    @app.post("/api/clear_spoof")
    def clear_spoof():
        b = request.get_json(force=True)
        srv = sites.get(b["site"])
        if srv:
            srv.unit.lt.spoof_active = False
        return jsonify({"ok": True})

    @app.post("/api/scenario")
    def scenario():
        b = request.get_json(force=True)
        if b["action"] == "start":
            engine.start(b["id"])
        else:
            engine.stop()
        return jsonify({"ok": True})

    return app


HTML = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OT Workflow Training</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Saira:wght@300;400;500;600&family=Saira+Condensed:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0e14;--pn:#111722;--pn2:#18202d;--ln:#283340;--tx:#e7edf3;--mut:#8a99ab;
--ac:#f2a431;--cy:#3fc1cf;--ok:#54c98c;--wn:#f2a431;--cr:#ef5b52;
--head:'Saira Condensed',sans-serif;--body:'Saira',sans-serif;}
*{box-sizing:border-box;font-family:var(--body)}
body{margin:0;color:var(--tx);font-size:14px;padding:0 16px 18px;
background:radial-gradient(1100px 460px at 72% -8%,#16202e 0%,var(--bg) 60%) fixed}
h1{font-family:var(--head);font-weight:700;font-size:30px;margin:0;letter-spacing:1px;line-height:1}
.sub{color:#c4d0dc;font-size:13px;margin-top:6px;max-width:560px;line-height:1.45}
a.out{position:absolute;top:16px;right:18px;color:#cdd9e4;font-size:12px;text-decoration:none;
font-family:var(--head);letter-spacing:.5px;text-transform:uppercase;
background:rgba(10,14,20,.45);padding:5px 10px;border:1px solid rgba(255,255,255,.18);border-radius:7px}
a.out:hover{border-color:var(--ac)}
.hero{position:relative;margin:14px 0;border-radius:14px;overflow:hidden;
height:clamp(150px,21vw,196px);border:1px solid var(--ln)}
.heroart{position:absolute;inset:0;width:100%;height:100%}
.scrim{position:absolute;inset:0;background:
linear-gradient(90deg,rgba(7,11,18,.93),rgba(7,11,18,.45) 48%,rgba(7,11,18,.05)),
linear-gradient(0deg,rgba(7,11,18,.75),transparent 55%)}
.htxt{position:absolute;left:0;bottom:0;padding:16px 22px}
.kicker{font-family:var(--head);text-transform:uppercase;letter-spacing:2px;font-size:11px;
color:var(--ac);margin-bottom:6px;font-weight:600}
.tabs{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap}
.tab{font-family:var(--head);text-transform:uppercase;letter-spacing:.6px;font-size:13px;
padding:8px 14px;border:1px solid var(--ln);border-radius:8px;cursor:pointer;background:var(--pn)}
.tab:hover{border-color:var(--ac)}
.tab.on{background:var(--ac);color:#1a1206;border-color:var(--ac);font-weight:600}
.view{display:none}.view.on{display:block}
.learn{display:flex;gap:14px;align-items:flex-start;flex-wrap:wrap}
.ladder{width:206px;flex-shrink:0}
.rung{border:1px solid var(--ln);border-left-width:4px;border-radius:0 8px 8px 0;
background:var(--pn);padding:9px 11px;margin-bottom:6px;cursor:pointer;transition:background .15s}
.rung:hover{border-color:var(--ac);background:var(--pn2)} .rung.on{background:var(--pn2);border-color:var(--ac)}
.rung b{font-family:var(--head);letter-spacing:.5px;font-size:14px;font-weight:600}
.rung .rt{font-size:11px;color:var(--mut)} .rung .done{float:right;color:var(--ok)}
.lesson{flex:1;min-width:280px;background:var(--pn);border:1px solid var(--ln);
border-radius:12px;padding:18px}
.lesson>div:first-child b{font-family:var(--head);letter-spacing:.5px}
.zbadge{display:inline-block;font-family:var(--head);text-transform:uppercase;letter-spacing:.5px;
font-size:11px;padding:2px 8px;border-radius:11px;margin-left:8px}
.z-IC{background:rgba(125,140,160,.16);color:#aab7c6;border:1px solid #54627a}
.z-OT{background:rgba(242,164,49,.16);color:#f4bd6a;border:1px solid #9a6916}
.z-Boundary{background:rgba(224,122,53,.16);color:#f0a06a;border:1px solid #93501f}
.z-IS{background:rgba(63,193,207,.16);color:#7fd6e0;border:1px solid #1f7a84}
.what{line-height:1.6;margin:12px 0 14px;color:#d6e0ea}
.lbl{font-family:var(--head);font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:1.5px;margin-top:14px}
.chips{margin-top:6px}
.chip{display:inline-block;background:var(--pn2);border:1px solid var(--ln);border-radius:13px;
padding:4px 11px;margin:4px 5px 0 0;font-size:12px}
.flow{margin-top:6px;padding:8px 11px;border-radius:8px;background:var(--pn2);border:1px solid var(--ln)}
.flow .a{font-family:var(--head);color:var(--ac);font-weight:600;margin-right:7px;text-transform:uppercase;letter-spacing:.5px}
.live{margin-top:14px;border:1px solid var(--ln);border-left:3px solid var(--cy);border-radius:8px;background:#0b1018;padding:13px}
.live h4{font-family:var(--head);margin:0 0 9px;font-size:11px;color:var(--cy);text-transform:uppercase;letter-spacing:1.5px}
.kv{display:flex;gap:16px;flex-wrap:wrap}
.kv div .n{font-size:11px;color:var(--mut)} .kv div .v{font-family:var(--head);font-size:20px;font-weight:600}
.tank{position:relative;width:54px;height:112px;border:2px solid var(--ln);border-radius:7px;
overflow:hidden;background:#0b1018} .liq{position:absolute;bottom:0;left:0;right:0;
background:linear-gradient(#15707c,#3fc1cf);transition:height .3s}
.pill{display:inline-block;font-family:var(--head);letter-spacing:.5px;padding:2px 8px;border-radius:11px;font-size:11px;font-weight:600}
.on2{background:rgba(84,201,140,.16);color:var(--ok);border:1px solid var(--ok)}
.off2{background:rgba(138,153,171,.14);color:var(--mut);border:1px solid var(--mut)}
.cr2{background:rgba(239,91,82,.16);color:var(--cr);border:1px solid var(--cr)}
.wn2{background:rgba(242,164,49,.16);color:var(--wn);border:1px solid var(--wn)}
.quiz{margin-top:14px;border-top:1px solid var(--ln);padding-top:13px}
.qopt{display:block;width:100%;text-align:left;margin:6px 0;padding:10px;background:var(--pn2);
border:1px solid var(--ln);border-radius:8px;color:var(--tx);cursor:pointer;font-size:13px}
.qopt:hover{border-color:var(--ac)} .qopt.right{border-color:var(--ok);background:rgba(84,201,140,.12)}
.qopt.wrong{border-color:var(--cr);background:rgba(239,91,82,.12)}
.explain{margin-top:9px;font-size:12px;color:var(--mut);line-height:1.55}
.nav{display:flex;justify-content:space-between;align-items:center;margin-top:16px}
button{font-family:var(--head);letter-spacing:.4px;background:var(--pn2);color:var(--tx);
border:1px solid var(--ln);border-radius:8px;padding:8px 15px;cursor:pointer;font-size:13px}
button:hover{border-color:var(--ac)} button.pri{background:var(--ac);color:#1a1206;border:0;font-weight:600;text-transform:uppercase}
button:disabled{opacity:.4;cursor:default}
.prog{font-family:var(--head);letter-spacing:.5px;font-size:12px;color:var(--mut)}
.bar{height:6px;background:var(--pn2);border-radius:3px;margin:14px 0 0;overflow:hidden}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--ac),var(--cy));transition:width .3s}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(244px,1fr));gap:12px}
.card{background:var(--pn);border:1px solid var(--ln);border-radius:12px;padding:13px}
.ev{padding:5px 9px;border-left:3px solid var(--ln);margin:3px 0;background:var(--pn);font-size:12px}
.ev.CRITICAL{border-color:var(--cr)} .ev.HIGH{border-color:var(--wn)} .ev .k{color:var(--mut);font-size:10px}
table{width:100%;border-collapse:collapse;font-size:12px} td,th{border:1px solid var(--ln);padding:6px;text-align:left}
th{font-family:var(--head);text-transform:uppercase;letter-spacing:.5px;font-weight:600;color:var(--mut)}
.toast{position:relative;margin-top:8px;padding:9px 11px;border-radius:8px;font-size:12px;
background:rgba(242,164,49,.14);border:1px solid var(--ac)}
.n{font-size:11px;color:var(--mut)}
</style></head><body>
<div class="hero">
  <svg class="heroart" viewBox="0 0 1200 220" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#0a1326"/><stop offset="50%" stop-color="#1d2c4d"/>
        <stop offset="74%" stop-color="#5b3b54"/><stop offset="88%" stop-color="#b9683b"/>
        <stop offset="100%" stop-color="#e69248"/></linearGradient>
      <radialGradient id="sun" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#ffd9a0"/><stop offset="42%" stop-color="#f0a24e" stop-opacity=".85"/>
        <stop offset="100%" stop-color="#f0a24e" stop-opacity="0"/></radialGradient>
      <linearGradient id="flame" x1="0" y1="1" x2="0" y2="0">
        <stop offset="0%" stop-color="#e0431a"/><stop offset="45%" stop-color="#ff8a1e"/>
        <stop offset="100%" stop-color="#ffd24a"/></linearGradient>
      <radialGradient id="fglow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#ff9b2e" stop-opacity=".55"/><stop offset="100%" stop-color="#ff9b2e" stop-opacity="0"/></radialGradient>
    </defs>
    <rect width="1200" height="220" fill="url(#sky)"/>
    <circle cx="180" cy="30" r="1.2" fill="#dce8f7" opacity=".6"/>
    <circle cx="420" cy="22" r="1" fill="#dce8f7" opacity=".5"/>
    <circle cx="760" cy="34" r="1.1" fill="#dce8f7" opacity=".5"/>
    <circle cx="1010" cy="20" r="1" fill="#dce8f7" opacity=".5"/>
    <ellipse cx="650" cy="172" rx="200" ry="130" fill="url(#sun)"/>
    <circle cx="650" cy="176" r="44" fill="#f4ad5c" opacity=".9"/>
    <rect x="0" y="150" width="1200" height="40" fill="#e08a40" opacity=".08"/>
    <g fill="#11203a">
      <rect x="78" y="120" width="9" height="46"/><rect x="92" y="106" width="7" height="60"/>
      <rect x="106" y="128" width="11" height="38"/><circle cx="150" cy="150" r="16"/>
      <rect x="980" y="116" width="9" height="50"/><rect x="994" y="104" width="7" height="62"/>
      <rect x="1008" y="126" width="11" height="40"/>
    </g>
    <rect x="0" y="164" width="1200" height="56" fill="#070c15"/>
    <rect x="0" y="163" width="1200" height="2" fill="#22324d" opacity=".55"/>
    <g fill="#05080f">
      <rect x="0" y="188" width="1200" height="9" rx="4"/>
      <rect x="210" y="196" width="9" height="24"/><rect x="520" y="196" width="9" height="24"/>
      <rect x="860" y="196" width="9" height="24"/><rect x="1080" y="196" width="9" height="24"/>
      <rect x="432" y="120" width="188" height="44" rx="22"/>
      <polygon points="455,164 470,164 466,196 451,196"/><polygon points="582,164 597,164 601,196 586,196"/>
      <rect x="236" y="108" width="9" height="56"/><rect x="222" y="120" width="37" height="7"/><rect x="226" y="134" width="29" height="6"/><rect x="231" y="100" width="19" height="9"/>
      <rect x="700" y="112" width="9" height="52"/><rect x="687" y="123" width="35" height="7"/><rect x="691" y="136" width="27" height="6"/><rect x="695" y="104" width="19" height="9"/>
      <rect x="1116" y="74" width="9" height="90"/>
    </g>
    <ellipse cx="1120" cy="58" rx="34" ry="42" fill="url(#fglow)"/>
    <path d="M1112 76 Q1108 54 1120 40 Q1132 54 1128 76 Z" fill="url(#flame)"/>
  </svg>
  <div class="scrim"></div>
  <a class="out" href="/logout">sign out</a>
  <div class="htxt">
    <div class="kicker">Upstream control systems &middot; live simulation</div>
    <h1>OT Workflow Training</h1>
    <div class="sub">A guided tour of the operational technology stack, Level 0 to Level 5, over a live well-control simulation.</div>
  </div>
</div>
<div class="tabs">
  <div class="tab on" data-v="learn" onclick="show('learn',this)">Learn the OT stack</div>
  <div class="tab" data-v="cr" onclick="show('cr',this)">Live control room</div>
  <div class="tab" data-v="siem" onclick="show('siem',this)">SIEM</div>
  <div class="tab" data-v="hist" onclick="show('hist',this)">Historian</div>
</div>

<div id="learn" class="view on">
  <div class="bar"><i id="pbar" style="width:0%"></i></div>
  <div class="prog" id="ptext" style="margin:6px 0 12px"></div>
  <div class="learn">
    <div class="ladder" id="ladder"></div>
    <div class="lesson" id="lesson"></div>
  </div>
</div>

<div id="cr" class="view"><div class="cards" id="cards"></div></div>
<div id="siem" class="view"><div id="events"></div></div>
<div id="hist" class="view"><div id="kpis"></div></div>

<script>
let CUR=[], idx=0, answered={}, latest={}, FIRST=null;

function show(v,el){document.querySelectorAll('.view').forEach(x=>x.classList.remove('on'));
 document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
 document.getElementById(v).classList.add('on'); el.classList.add('on');}

function pill(on,txt,cls){return `<span class="pill ${cls||(on?'on2':'off2')}">${txt}</span>`}

async function cmd(site,tag,value){return fetch('/api/command',{method:'POST',
 headers:{'Content-Type':'application/json'},body:JSON.stringify({site,tag,value})});}

/* ---------- live panels per level ---------- */
function firstSite(){const k=Object.keys(latest.sites||{});return k.length?latest.sites[FIRST||k[0]]||latest.sites[k[0]]:null;}
function livePanel(key){
  const s=firstSite();
  if(!s && key!=='siem' && key!=='dmz' && key!=='historian') return '<span class="sub">connecting to the plant…</span>';
  if(key==='instrument'){
    return `<div style="display:flex;gap:16px;align-items:center">
      <div class="tank"><div class="liq" style="height:${s.Level_PV}%"></div></div>
      <div class="kv">
        <div><div class="n">Level transmitter</div><div class="v">${(+s.Level_PV).toFixed(1)}%</div></div>
        <div><div class="n">Pressure transmitter</div><div class="v">${(+s.Pressure_PV).toFixed(0)} kPa</div></div>
        <div><div class="n">Inlet valve</div><div class="v">${(+s.Valve_MV).toFixed(0)}%</div></div>
        <div><div class="n">Discharge pump</div><div class="v">${pill(s.Pump_Run,s.Pump_Run?'RUNNING':'STOPPED')}</div></div>
      </div></div>
      <div class="explain">These are the raw field signals from one separator skid. Nothing here decides anything - it only measures and moves.</div>`;
  }
  if(key==='control'){
    return `<div class="kv">
      <div><div class="n">Setpoint (target)</div><div class="v">${(+s.Level_SP).toFixed(0)}%</div></div>
      <div><div class="n">Measured level</div><div class="v">${(+s.Level_PV).toFixed(1)}%</div></div>
      <div><div class="n">Control mode</div><div class="v">${pill(s.Mode_Auto,s.Mode_Auto?'AUTO':'MANUAL',s.Mode_Auto?'on2':'wn2')}</div></div>
      <div><div class="n">Valve output</div><div class="v">${(+s.Valve_MV).toFixed(0)}%</div></div>
      <div><div class="n">Safety trip (SIS)</div><div class="v">${pill(0,s.SIS_Trip?'TRIPPED':'NORMAL',s.SIS_Trip?'cr2':'on2')}</div></div>
    </div>
    <div class="explain">The PLC compares measured level to the setpoint and modulates the valve to hold it. The SIS watches independently and trips the plant if level reaches high-high.</div>`;
  }
  if(key==='scada'){
    const rows=Object.entries(latest.sites||{}).map(([k,v])=>`<tr><td>${k}</td>
      <td>${(+v.Level_PV).toFixed(1)}%</td><td>${pill(v.Mode_Auto,v.Mode_Auto?'AUTO':'MAN',v.Mode_Auto?'on2':'wn2')}</td>
      <td>${v.SIS_Trip?pill(0,'TRIP','cr2'):(v.Alarm_H||v.Alarm_HH?pill(0,'HIGH','wn2'):pill(1,'ok'))}</td></tr>`).join('');
    return `<table><tr><th>Asset</th><th>Level</th><th>Mode</th><th>Status</th></tr>${rows}</table>
      <div class="explain">An operator's supervisory view: every loop's value, mode and alarm state at a glance, with the controls to act on them.</div>`;
  }
  if(key==='controlroom'){
    const ss=Object.values(latest.sites||{});const auto=ss.filter(x=>x.Mode_Auto).length;
    const trips=ss.filter(x=>x.SIS_Trip).length;const alarms=ss.filter(x=>x.Alarm_H||x.Alarm_HH||x.Alarm_L||x.Alarm_LL).length;
    return `<div class="kv">
      <div><div class="n">Sites operated</div><div class="v">${ss.length}</div></div>
      <div><div class="n">In auto control</div><div class="v">${auto}/${ss.length}</div></div>
      <div><div class="n">Safety trips</div><div class="v">${pill(0,trips,trips?'cr2':'on2')}</div></div>
      <div><div class="n">Active alarms</div><div class="v">${pill(0,alarms,alarms?'wn2':'on2')}</div></div>
    </div>
    <div class="explain">One picture across Cooper, Roma-CSG and PNG together - the whole-of-field view the central control room works from.</div>`;
  }
  if(key==='siem'){
    const evs=(latest.events||[]).slice(0,7);
    const body=evs.length?evs.map(e=>`<div class="ev ${e.severity}"><span class="k">${e.kind} · ${e.source}</span><br>${e.message}</div>`).join(''):'<span class="sub">No events - all systems nominal.</span>';
    return body+'<div class="explain">The SIEM watches the OT systems and raises an event when something is off - an unexpected change, a safety bypass, or loss of comms.</div>';
  }
  if(key==='dmz'){
    const led=(latest.ledger||[]).slice(0,6);
    const body=led.length?'<table><tr><th>Time</th><th>Asset</th><th>Change</th><th>By</th></tr>'+
      led.map(l=>`<tr><td>${new Date(l.ts*1000).toLocaleTimeString()}</td><td>${l.site}</td><td>${l.tag}=${l.value}</td><td>${l.user}</td></tr>`).join('')+'</table>'
      :'<span class="sub">No crossings logged yet. Run the demonstration to send one through the gateway.</span>';
    return body+`<button class="pri" style="margin-top:10px" onclick="demoGateway()">Run a demonstration</button>
      <div id="demotoast"></div>
      <div class="explain">Every change that crosses the boundary is brokered and logged here. Press the button to push one sanctioned setpoint change through the gateway and watch it appear in the audit log.</div>`;
  }
  if(key==='historian'){
    const k=latest.kpis||{};const rows=Object.entries(k).map(([s,v])=>`<tr><td>${s}</td><td>${v.avg_throughput}</td><td>${v.samples}</td></tr>`).join('');
    return `<table><tr><th>Asset</th><th>Avg throughput m³/h</th><th>Samples stored</th></tr>${rows||'<tr><td colspan=3>warming up…</td></tr>'}</table>
      <div class="explain">The historian stores every reading over time. The business analyses this data - it never sends commands back to the plant.</div>`;
  }
  return '';
}

async function demoGateway(){
  const s=firstSite(); if(!s) return;
  const k=FIRST||Object.keys(latest.sites)[0];
  const nv=Math.max(30,Math.min(75,Math.round((+s.Level_SP)+ (s.Level_SP<55?8:-8))));
  await cmd(k,'Level_SP',nv);
  document.getElementById('demotoast').innerHTML=`<div class="toast">Sent setpoint ${nv}% to ${k} through the gateway. It will appear in the audit log below.</div>`;
}

/* ---------- lesson rendering ---------- */
function renderLadder(){
  document.getElementById('ladder').innerHTML=CUR.slice().reverse().map(l=>{
      const i=CUR.indexOf(l);const z=l.zone.replace('&','').replace('/','');
      return `<div class="rung z-${z} ${i===idx?'on':''}" style="border-left-color:${zoneColor(l.zone)}" onclick="goto(${i})">
        ${answered[l.id]!==undefined?'<span class="done">✓</span>':''}
        <b>${l.code}</b><div class="rt">${l.title}</div></div>`}).join('');
}
function zoneColor(z){return z==='IS'?'#3fc1cf':z==='OT'?'#f2a431':z==='Boundary'?'#e07a35':'#7d8ca0';}

function renderLesson(){
  const l=CUR[idx];
  const chips=l.lives.map(x=>`<span class="chip">${x}</span>`).join('');
  const ans=answered[l.id];
  const opts=l.quiz.options.map((o,i)=>{
    let cls=''; if(ans!==undefined){if(i===l.quiz.answer)cls='right';else if(i===ans)cls='wrong';}
    return `<button class="qopt ${cls}" ${ans!==undefined?'disabled':''} onclick="answer(${i})">${o}</button>`}).join('');
  const z=l.zone.replace('&','').replace('/','');
  document.getElementById('lesson').innerHTML=`
    <div><b style="font-size:15px">${l.code}: ${l.title}</b><span class="zbadge z-${z}">${l.zone} zone</span></div>
    <div class="what">${l.what}</div>
    <div class="lbl">What lives here</div><div class="chips">${chips}</div>
    <div class="lbl">Data flow</div>
    <div class="flow"><span class="a">▲ up</span>${l.up}</div>
    <div class="flow"><span class="a">▼ down</span>${l.down}</div>
    <div class="live"><h4>Live from the running plant</h4><div id="livebody">${livePanel(l.live)}</div></div>
    <div class="quiz"><div class="lbl">Knowledge check</div>
      <div style="margin:6px 0 4px">${l.quiz.q}</div>${opts}
      ${ans!==undefined?`<div class="explain">${l.quiz.explain}</div>`:''}
    </div>
    <div class="nav">
      <button onclick="goto(${idx-1})" ${idx===0?'disabled':''}>‹ Previous</button>
      <span class="prog">Level ${idx+1} of ${CUR.length}</span>
      <button class="pri" onclick="next()">${idx===CUR.length-1?'Finish':'Next ›'}</button>
    </div>`;
  renderLadder(); updateProgress();
}
function answer(i){const l=CUR[idx];answered[l.id]=i;renderLesson();}
function goto(i){if(i<0||i>=CUR.length)return;idx=i;renderLesson();}
function next(){if(idx<CUR.length-1){idx++;renderLesson();}else{finish();}}
function updateProgress(){const done=Object.keys(answered).length;
  document.getElementById('pbar').style.width=(done/CUR.length*100)+'%';
  document.getElementById('ptext').textContent=`${done} of ${CUR.length} knowledge checks complete`;}
function finish(){
  const done=Object.keys(answered).length;
  document.getElementById('lesson').innerHTML=`<div style="text-align:center;padding:20px">
    <b style="font-size:16px">OT workflow overview complete</b>
    <p class="what">You have walked the full stack from the physical process at Level 0 up to the business systems at Level 4/5, and seen the live simulation at each layer.</p>
    <p class="prog">${done} of ${CUR.length} knowledge checks answered.</p>
    <button class="pri" onclick="idx=0;renderLesson()">Start over</button>
    <button onclick="document.querySelector('.tab[data-v=cr]').click()">Explore the live control room</button>
  </div>`;
  document.getElementById('pbar').style.width='100%';
}

/* ---------- operational views ---------- */
function renderOps(d){
  document.getElementById('cards').innerHTML=Object.entries(d.sites).map(([k,s])=>`
    <div class="card"><div style="font-weight:bold">${k}
      ${s.SIS_Trip?pill(0,'SIS TRIP','cr2'):''}</div>
      <div style="display:flex;gap:12px;margin-top:8px;align-items:center">
      <div class="tank"><div class="liq" style="height:${s.Level_PV}%"></div></div>
      <div><div class="n">Level</div><div style="font-size:18px;font-weight:bold">${(+s.Level_PV).toFixed(1)}%</div>
      <div style="margin-top:6px">${pill(s.Mode_Auto,s.Mode_Auto?'AUTO':'MANUAL',s.Mode_Auto?'on2':'wn2')} ${pill(s.Pump_Run,s.Pump_Run?'PUMP':'OFF')}</div></div>
    </div></div>`).join('');
  document.getElementById('events').innerHTML=(d.events||[]).map(e=>
    `<div class="ev ${e.severity}"><span class="k">${new Date(e.ts*1000).toLocaleTimeString()} · ${e.kind} · ${e.source}</span><br>${e.message}</div>`).join('')||'<div class="sub">No events.</div>';
  const rows=Object.entries(d.kpis).map(([s,v])=>`<tr><td>${s}</td><td>${v.avg_throughput}</td><td>${v.samples}</td></tr>`).join('');
  document.getElementById('kpis').innerHTML=`<table><tr><th>Asset</th><th>Avg throughput m³/h</th><th>Samples</th></tr>${rows||'<tr><td colspan=3>warming up…</td></tr>'}</table>`;
}

async function poll(){
  try{latest=await(await fetch('/api/state')).json();
    if(!FIRST)FIRST=Object.keys(latest.sites)[0];
    const lb=document.getElementById('livebody');
    if(lb && document.getElementById('learn').classList.contains('on')) lb.innerHTML=livePanel(CUR[idx].live);
    renderOps(latest);
  }catch(e){}
}
async function boot(){
  CUR=await(await fetch('/api/curriculum')).json();
  await poll(); renderLesson(); setInterval(poll,1000);
}
boot();
</script></body></html>"""
