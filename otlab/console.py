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
<title>OT Workflow Training</title><style>
:root{--bg:#0d1117;--pn:#161b22;--pn2:#1c2430;--ln:#30363d;--tx:#c9d1d9;--mut:#8b949e;
--ac:#58a6ff;--ok:#3fb950;--wn:#d29922;--cr:#f85149;}
*{box-sizing:border-box;font-family:Consolas,Menlo,monospace}
body{margin:0;background:var(--bg);color:var(--tx);padding:14px;font-size:13px}
h1{font-size:15px;margin:0 0 2px;letter-spacing:1px}
.sub{color:var(--mut);font-size:11px;margin-bottom:12px}
a.out{color:var(--mut);font-size:11px;text-decoration:none;float:right}
.tabs{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
.tab{padding:6px 12px;border:1px solid var(--ln);border-radius:6px;cursor:pointer;background:var(--pn)}
.tab.on{background:var(--ac);color:#0d1117;border-color:var(--ac)}
.view{display:none}.view.on{display:block}
/* Learn layout */
.learn{display:flex;gap:14px;align-items:flex-start;flex-wrap:wrap}
.ladder{width:200px;flex-shrink:0}
.rung{border:1px solid var(--ln);border-left-width:4px;border-radius:0 6px 6px 0;
background:var(--pn);padding:8px 10px;margin-bottom:6px;cursor:pointer}
.rung:hover{border-color:var(--ac)} .rung.on{background:var(--pn2)}
.rung b{font-size:12px} .rung .rt{font-size:10px;color:var(--mut)}
.rung .done{float:right;color:var(--ok)}
.lesson{flex:1;min-width:280px;background:var(--pn);border:1px solid var(--ln);
border-radius:8px;padding:16px}
.zbadge{display:inline-block;font-size:10px;padding:2px 7px;border-radius:10px;margin-left:8px}
.z-IC{background:rgba(139,148,158,.16);color:#b4b2a9;border:1px solid #5f5e5a}
.z-OT{background:rgba(29,158,117,.16);color:#5dcaa5;border:1px solid #0f6e56}
.z-Boundary{background:rgba(210,153,34,.16);color:#f0c674;border:1px solid #854f0b}
.z-IS{background:rgba(55,138,221,.16);color:#85b7eb;border:1px solid #185fa5}
.what{line-height:1.6;margin:10px 0 14px}
.lbl{font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:1px;margin-top:12px}
.chips{margin-top:6px}
.chip{display:inline-block;background:var(--pn2);border:1px solid var(--ln);border-radius:12px;
padding:3px 9px;margin:3px 4px 0 0;font-size:11px}
.flow{margin-top:6px;padding:7px 10px;border-radius:6px;background:var(--pn2);border:1px solid var(--ln)}
.flow .a{color:var(--ac);font-weight:bold;margin-right:6px}
.live{margin-top:14px;border:1px solid var(--ln);border-radius:8px;background:#0a0e13;padding:12px}
.live h4{margin:0 0 8px;font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:1px}
.kv{display:flex;gap:14px;flex-wrap:wrap}
.kv div .n{font-size:10px;color:var(--mut)} .kv div .v{font-size:18px;font-weight:bold}
.tank{position:relative;width:54px;height:110px;border:2px solid var(--ln);border-radius:6px;
overflow:hidden;background:#0a0e13} .liq{position:absolute;bottom:0;left:0;right:0;
background:linear-gradient(#1f6feb,#388bfd);transition:height .3s}
.pill{display:inline-block;padding:2px 7px;border-radius:10px;font-size:10px;font-weight:bold}
.on2{background:rgba(63,185,80,.16);color:var(--ok);border:1px solid var(--ok)}
.off2{background:rgba(139,148,158,.14);color:var(--mut);border:1px solid var(--mut)}
.cr2{background:rgba(248,81,73,.16);color:var(--cr);border:1px solid var(--cr)}
.wn2{background:rgba(210,153,34,.16);color:var(--wn);border:1px solid var(--wn)}
.quiz{margin-top:14px;border-top:1px solid var(--ln);padding-top:12px}
.qopt{display:block;width:100%;text-align:left;margin:6px 0;padding:9px;background:var(--pn2);
border:1px solid var(--ln);border-radius:6px;color:var(--tx);cursor:pointer;font-size:12px}
.qopt:hover{border-color:var(--ac)} .qopt.right{border-color:var(--ok);background:rgba(63,185,80,.12)}
.qopt.wrong{border-color:var(--cr);background:rgba(248,81,73,.12)}
.explain{margin-top:8px;font-size:12px;color:var(--mut);line-height:1.5}
.nav{display:flex;justify-content:space-between;align-items:center;margin-top:16px}
button{background:#21262d;color:var(--tx);border:1px solid var(--ln);border-radius:6px;
padding:7px 14px;cursor:pointer;font-family:inherit;font-size:12px}
button:hover{border-color:var(--ac)} button.pri{background:var(--ac);color:#0d1117;border:0;font-weight:bold}
button:disabled{opacity:.4;cursor:default}
.prog{font-size:11px;color:var(--mut)}
.bar{height:5px;background:var(--pn2);border-radius:3px;margin:8px 0 0;overflow:hidden}
.bar i{display:block;height:100%;background:var(--ac);transition:width .3s}
/* operational views */
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
.card{background:var(--pn);border:1px solid var(--ln);border-radius:8px;padding:12px}
.ev{padding:4px 8px;border-left:3px solid var(--ln);margin:3px 0;background:var(--pn);font-size:11px}
.ev.CRITICAL{border-color:var(--cr)} .ev.HIGH{border-color:var(--wn)} .ev .k{color:var(--mut);font-size:9px}
table{width:100%;border-collapse:collapse;font-size:11px} td,th{border:1px solid var(--ln);padding:5px;text-align:left}
.toast{position:relative;margin-top:8px;padding:8px 10px;border-radius:6px;font-size:11px;
background:rgba(88,166,255,.14);border:1px solid var(--ac)}
</style></head><body>
<a class="out" href="/logout">sign out</a>
<h1>OT WORKFLOW TRAINING</h1>
<div class="sub">A guided overview of the operational technology stack, Level 0 to Level 5, with a live simulation. This is a training simulation; no plant is connected.</div>
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
function zoneColor(z){return z==='IS'?'#378add':z==='OT'?'#1d9e75':z==='Boundary'?'#d29922':'#888780';}

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
