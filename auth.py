"""
otlab.auth  -  simple credential gate for the training console.

Every page and API route requires a logged-in session. Users come from the
environment so no secrets live in the code:

  OTLAB_SECRET   Flask session signing key (set a long random value).
  OTLAB_USERS    JSON of {username: password_hash}. Generate hashes with
                 make_user.py. Example:
                 OTLAB_USERS='{"sumit":"pbkdf2:sha256:...", "trainee1":"..."}'

If OTLAB_USERS is not set, the app will NOT run wide open: it generates a
random admin password at start-up and prints it once to the logs, so you can
get in, then set real users via OTLAB_USERS.
"""

import json
import os
import secrets

from flask import (redirect, render_template_string, request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

_LOGIN_HTML = r"""<!doctype html><html lang=en><head><meta charset=utf-8>
<title>Onshore Controls and OT Training</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<link rel=preconnect href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Saira:wght@300;400;500;600&family=Saira+Condensed:wght@500;600;700&display=swap" rel=stylesheet>
<style>
:root{--bg0:#070b11;--bg1:#0c1622;--ac:#f2a431;--cy:#3fc1cf;--ln:#1d2a38;
--txt:#e7edf3;--mut:#8a99ab}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg0);color:var(--txt);font-family:'Saira',sans-serif;
overflow:hidden}
.scene{position:fixed;inset:0;z-index:0}
.scene svg{width:100%;height:100%;display:block}
.vig{position:fixed;inset:0;z-index:1;pointer-events:none;
background:radial-gradient(120% 90% at 70% 40%,transparent 30%,rgba(4,7,11,.55) 78%,rgba(4,7,11,.9) 100%)}
.wrap{position:fixed;inset:0;z-index:2;display:flex;align-items:center;
justify-content:center;padding:24px}
.card{width:370px;max-width:94vw;background:rgba(12,20,30,.82);
backdrop-filter:blur(9px);-webkit-backdrop-filter:blur(9px);
border:1px solid var(--ln);border-radius:16px;padding:30px 28px 26px;
box-shadow:0 30px 80px rgba(0,0,0,.55),0 0 0 1px rgba(63,193,207,.06)}
.kick{font-family:'Saira Condensed',sans-serif;text-transform:uppercase;
letter-spacing:3px;font-size:11px;color:var(--ac);font-weight:600;margin-bottom:10px;
display:flex;align-items:center;gap:8px}
.dot{width:7px;height:7px;border-radius:50%;background:#54c98c;
box-shadow:0 0 9px #54c98c;animation:pulse 1.8s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
h1{font-family:'Saira Condensed',sans-serif;font-weight:700;font-size:27px;
line-height:1.08;margin:0 0 6px;letter-spacing:.4px}
h1 span{color:var(--cy)}
.by{font-size:13px;color:var(--mut);margin-bottom:3px}
.by b{color:var(--txt);font-weight:500}
.sub{font-size:11.5px;color:var(--mut);letter-spacing:.3px;margin-bottom:20px}
label{font-family:'Saira Condensed',sans-serif;text-transform:uppercase;
letter-spacing:1.2px;font-size:10px;color:var(--mut);display:block;margin:0 0 5px 2px}
input{width:100%;margin-bottom:14px;padding:11px 12px;background:#0a121c;
border:1px solid var(--ln);border-radius:9px;color:var(--txt);
font-family:inherit;font-size:14px;transition:border-color .15s,box-shadow .15s}
input:focus{outline:0;border-color:var(--cy);box-shadow:0 0 0 3px rgba(63,193,207,.16)}
button{width:100%;margin-top:4px;padding:12px;border:0;border-radius:9px;cursor:pointer;
font-family:'Saira Condensed',sans-serif;text-transform:uppercase;letter-spacing:1.5px;
font-weight:700;font-size:13px;color:#0a141a;
background:linear-gradient(135deg,var(--ac),#f0b860)}
button:hover{filter:brightness(1.06)}
.err{color:#f3766b;font-size:12px;margin-top:12px;text-align:center}
.foot{margin-top:18px;padding-top:14px;border-top:1px solid var(--ln);
font-size:10.5px;color:var(--mut);letter-spacing:.4px;text-align:center}
@keyframes flame{0%,100%{transform:scaleY(1) translateY(0);opacity:.9}
50%{transform:scaleY(1.18) translateY(-3px);opacity:1}}
.flame{transform-origin:center bottom;animation:flame 1.3s ease-in-out infinite}
@media(max-width:640px){h1{font-size:23px}.card{padding:26px 22px}}
</style></head><body>
<div class=scene>
<svg viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#0a1521"/><stop offset="55%" stop-color="#0a1019"/>
<stop offset="100%" stop-color="#05080d"/></linearGradient>
<radialGradient id="glow" cx="68%" cy="78%" r="60%">
<stop offset="0" stop-color="#23506a" stop-opacity=".55"/>
<stop offset="100%" stop-color="#23506a" stop-opacity="0"/></radialGradient>
<linearGradient id="scr" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#0e2230"/><stop offset="100%" stop-color="#091824"/></linearGradient>
<linearGradient id="liq" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#2f9fb0"/><stop offset="100%" stop-color="#1c6675"/></linearGradient>
<filter id="soft" x="-40%" y="-40%" width="180%" height="180%">
<feGaussianBlur stdDeviation="3.2"/></filter>
</defs>

<rect width="1440" height="900" fill="url(#sky)"/>
<rect width="1440" height="900" fill="url(#glow)"/>

<!-- perspective floor -->
<g stroke="#16384a" stroke-width="1" opacity=".35">
<line x1="720" y1="640" x2="-120" y2="900"/><line x1="720" y1="640" x2="360" y2="900"/>
<line x1="720" y1="640" x2="720" y2="900"/><line x1="720" y1="640" x2="1080" y2="900"/>
<line x1="720" y1="640" x2="1560" y2="900"/>
<line x1="120" y1="720" x2="1320" y2="720"/><line x1="20" y1="800" x2="1420" y2="800"/>
</g>

<!-- far oil & gas silhouette: pipeline, wellheads, flare -->
<g opacity=".5">
<rect x="0" y="600" width="1440" height="7" fill="#11212e"/>
<g fill="#0f1f2b">
<rect x="170" y="560" width="9" height="45"/><rect x="158" y="552" width="33" height="12"/>
<rect x="166" y="540" width="17" height="10"/>
<rect x="250" y="566" width="8" height="39"/><rect x="240" y="558" width="28" height="11"/>
</g>
<!-- flare stack -->
<rect x="1300" y="470" width="13" height="138" fill="#10212d"/>
<g class="flame"><path d="M1306 470 q-16 -26 0 -52 q16 26 0 52z" fill="#f2a431"/>
<path d="M1306 462 q-9 -16 0 -32 q9 16 0 32z" fill="#ffd98a"/></g>
</g>

<!-- data-flow paths rising to the portal (top right) -->
<g fill="none" stroke="#2a6f7d" stroke-width="2" opacity=".7">
<path id="f1" d="M560 470 C 700 360, 980 360, 1140 250"/>
<path id="f2" d="M720 500 C 860 420, 1020 330, 1150 260"/>
<path id="f3" d="M900 470 C 1000 410, 1080 320, 1160 252"/>
</g>
<g fill="#3fc1cf">
<circle r="3.4"><animateMotion dur="3.2s" repeatCount="indefinite"><mpath href="#f1"/></animateMotion></circle>
<circle r="3.4"><animateMotion dur="3.9s" begin="-1s" repeatCount="indefinite"><mpath href="#f2"/></animateMotion></circle>
<circle r="3.4"><animateMotion dur="3.5s" begin="-2s" repeatCount="indefinite"><mpath href="#f3"/></animateMotion></circle>
</g>

<!-- data portal / cloud -->
<g transform="translate(1150 230)">
<circle r="46" fill="none" stroke="#3fc1cf" stroke-width="1" opacity=".25"/>
<circle r="32" fill="none" stroke="#3fc1cf" stroke-width="1" opacity=".4"/>
<path d="M-30 6 a18 18 0 0 1 8 -34 a22 22 0 0 1 41 6 a16 16 0 0 1 -3 32 z"
fill="#0e2a33" stroke="#3fc1cf" stroke-width="1.5"/>
<circle r="4" fill="#3fc1cf" filter="url(#soft)"/>
<text x="0" y="62" text-anchor="middle" fill="#6f8597"
font-family="'Saira Condensed',sans-serif" font-size="13" letter-spacing="2">DATA PORTAL</text>
</g>

<!-- ===== video wall ===== -->
<!-- trend screen -->
<g transform="translate(250 250) skewY(4)">
<rect x="-8" y="-8" width="276" height="186" rx="10" fill="#0a141d" stroke="#1d2a38"/>
<rect width="260" height="170" rx="6" fill="url(#scr)"/>
<g stroke="#163143" stroke-width="1">
<line x1="0" y1="42" x2="260" y2="42"/><line x1="0" y1="85" x2="260" y2="85"/>
<line x1="0" y1="128" x2="260" y2="128"/></g>
<polyline points="0,120 30,96 60,104 90,70 120,82 150,48 180,62 210,40 240,58 260,46"
fill="none" stroke="#3fc1cf" stroke-width="2.4" stroke-dasharray="600"
stroke-dashoffset="600"><animate attributeName="stroke-dashoffset" from="600" to="0" dur="3s" repeatCount="indefinite"/></polyline>
<polyline points="0,140 30,132 60,138 90,120 120,128 150,112 180,122 210,108 240,118 260,110"
fill="none" stroke="#f2a431" stroke-width="2" opacity=".85" stroke-dasharray="600"
stroke-dashoffset="600"><animate attributeName="stroke-dashoffset" from="600" to="0" dur="3.6s" repeatCount="indefinite"/></polyline>
<rect width="260" height="16" fill="#0c1c27"/><circle cx="10" cy="8" r="3" fill="#54c98c"/>
<text x="22" y="12" fill="#6f8597" font-family="'Saira Condensed'" font-size="10" letter-spacing="1">TRENDS · SEP LEVEL / FLOW</text>
</g>

<!-- separator mimic screen (center) -->
<g transform="translate(560 205)">
<rect x="-10" y="-10" width="340" height="232" rx="12" fill="#0a141d" stroke="#1d2a38"/>
<rect width="320" height="212" rx="7" fill="url(#scr)"/>
<rect width="320" height="18" fill="#0c1c27"/>
<text x="10" y="13" fill="#7fd0db" font-family="'Saira Condensed'" font-size="11" letter-spacing="1.5">SEPARATOR  V-101</text>
<circle cx="304" cy="9" r="4" fill="#54c98c"><animate attributeName="opacity" values="1;.3;1" dur="1.6s" repeatCount="indefinite"/></circle>
<!-- vessel -->
<rect x="70" y="74" width="180" height="86" rx="43" fill="#0c1f2b" stroke="#2f6f7d" stroke-width="2"/>
<clipPath id="vc"><rect x="72" y="76" width="176" height="82" rx="41"/></clipPath>
<g clip-path="url(#vc)"><rect x="72" y="120" width="176" height="40" fill="url(#liq)">
<animate attributeName="y" values="120;112;120" dur="4s" repeatCount="indefinite"/>
<animate attributeName="height" values="40;48;40" dur="4s" repeatCount="indefinite"/></rect></g>
<!-- pipes -->
<path d="M20 100 h54" stroke="#2f6f7d" stroke-width="6" fill="none"/>
<path d="M246 96 h60 v-24" stroke="#2f6f7d" stroke-width="6" fill="none"/>
<path d="M160 160 v34 h120" stroke="#2f6f7d" stroke-width="6" fill="none"/>
<!-- valves -->
<g fill="#0c1f2b" stroke="#f2a431" stroke-width="1.6">
<path d="M300 64 l8 8 l-8 8 l-8 -8 z"/><path d="M280 194 l8 8 l-8 8 l-8 -8 z"/></g>
<!-- mini gauges -->
<g><circle cx="42" cy="150" r="16" fill="#0c1f2b" stroke="#1d3947"/>
<line x1="42" y1="150" x2="52" y2="142" stroke="#3fc1cf" stroke-width="2"><animateTransform attributeName="transform" type="rotate" from="-30 42 150" to="30 42 150" dur="3s" values="-30 42 150;28 42 150;-30 42 150" repeatCount="indefinite"/></line></g>
<text x="160" y="208" text-anchor="middle" fill="#5f7686" font-family="'Saira Condensed'" font-size="10" letter-spacing="1.5">LEVEL CONTROL · AUTO</text>
</g>

<!-- network topology screen -->
<g transform="translate(940 250) skewY(-4)">
<rect x="-8" y="-8" width="246" height="196" rx="10" fill="#0a141d" stroke="#1d2a38"/>
<rect width="230" height="180" rx="6" fill="url(#scr)"/>
<rect width="230" height="16" fill="#0c1c27"/>
<text x="8" y="12" fill="#6f8597" font-family="'Saira Condensed'" font-size="10" letter-spacing="1">OPC UA · NETWORK</text>
<line x1="115" y1="44" x2="115" y2="158" stroke="#234b59" stroke-width="2"/>
<g font-family="'Saira Condensed'" font-size="10" fill="#bcd2dc" text-anchor="middle">
<g><rect x="70" y="34" width="90" height="22" rx="5" fill="#0e2a33" stroke="#2f6f7d"/><text x="115" y="49">PLC · L1</text></g>
<g><rect x="70" y="72" width="90" height="22" rx="5" fill="#0e2a33" stroke="#2f6f7d"/><text x="115" y="87">SCADA · L2</text></g>
<g><rect x="70" y="110" width="90" height="22" rx="5" fill="#0e2a33" stroke="#f2a431"/><text x="115" y="125">OSG · DMZ</text></g>
<g><rect x="70" y="148" width="90" height="22" rx="5" fill="#0e2a33" stroke="#2f6f7d"/><text x="115" y="163">IP21 · L5</text></g></g>
<circle r="3" fill="#3fc1cf"><animateMotion dur="2.6s" repeatCount="indefinite" path="M115 56 L115 158"/></circle>
<circle r="3" fill="#f2a431"><animateMotion dur="2.6s" begin="-1.3s" repeatCount="indefinite" path="M115 158 L115 56"/></circle>
</g>

<!-- desk + operators -->
<g transform="translate(0 0)">
<rect x="470" y="540" width="500" height="20" rx="8" fill="#0e1f2b"/>
<rect x="500" y="486" width="120" height="60" rx="6" fill="#0a151e" stroke="#1d3140"/>
<rect x="508" y="492" width="104" height="48" rx="3" fill="#0c2430"/>
<rect x="820" y="486" width="120" height="60" rx="6" fill="#0a151e" stroke="#1d3140"/>
<rect x="828" y="492" width="104" height="48" rx="3" fill="#0c2430"/>
<g fill="#0a1119"><!-- operators -->
<g><ellipse cx="650" cy="500" rx="17" ry="18"/><path d="M620 552 q30 -40 60 0 z"/></g>
<g><ellipse cx="800" cy="500" rx="17" ry="18"/><path d="M770 552 q30 -40 60 0 z"/></g></g>
<path d="M634 500 a17 17 0 0 1 32 0" fill="none" stroke="#27566640" stroke-width="2"/>
<path d="M784 500 a17 17 0 0 1 32 0" fill="none" stroke="#27566640" stroke-width="2"/>
</g>

<!-- Purdue ladder left -->
<g transform="translate(70 250)" font-family="'Saira Condensed'" font-size="12" fill="#5f7686" opacity=".8">
<rect x="0" y="0" width="3" height="300" fill="#1d3947"/>
<g text-anchor="start">
<circle cx="1.5" cy="20" r="4" fill="#3fc1cf"/><text x="14" y="24">L5 · BUSINESS</text>
<circle cx="1.5" cy="75" r="4" fill="#3fc1cf"/><text x="14" y="79">L4 · IT / IP21</text>
<circle cx="1.5" cy="130" r="4" fill="#f2a431"/><text x="14" y="134">L3.5 · DMZ / OSG</text>
<circle cx="1.5" cy="185" r="4" fill="#3fc1cf"/><text x="14" y="189">L2 · SCADA</text>
<circle cx="1.5" cy="240" r="4" fill="#3fc1cf"/><text x="14" y="244">L1 · PLC</text>
<circle cx="1.5" cy="295" r="4" fill="#54c98c"/><text x="14" y="299">L0 · FIELD</text>
</g></g>
</svg>
</div>
<div class=vig></div>
<div class=wrap>
<form class=card method=post>
<div class=kick><span class=dot></span> Control room access</div>
<h1>Onshore Controls<br>and <span>OT Training</span></h1>
<div class=by>An initiative by <b>Sumit Mathew</b></div>
<div class=sub>Operational technology · The Purdue model, Level 0 to 5 · live simulation</div>
<label for=u>Username</label>
<input id=u name=username placeholder="your username" autofocus autocomplete=username>
<label for=p>Password</label>
<input id=p name=password type=password placeholder="your password" autocomplete=current-password>
<button>Sign in</button>
{% if error %}<div class=err>{{ error }}</div>{% endif %}
<div class=foot>Authorised users only · Training simulation environment</div>
</form>
</div>
</body></html>"""


def _load_users():
    raw = os.environ.get("OTLAB_USERS")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            print("[auth] OTLAB_USERS is not valid JSON - ignoring")
    # No users configured: create a temporary admin so we are never open.
    pw = secrets.token_urlsafe(12)
    print("=" * 60)
    print("[auth] OTLAB_USERS not set. Temporary login created:")
    print(f"[auth]   username: admin")
    print(f"[auth]   password: {pw}")
    print("[auth] Set OTLAB_USERS in the environment for real accounts.")
    print("=" * 60)
    return {"admin": generate_password_hash(pw)}


def install_auth(app):
    app.secret_key = os.environ.get("OTLAB_SECRET") or secrets.token_hex(32)
    users = _load_users()

    @app.before_request
    def _guard():
        if request.endpoint in ("login", "logout"):
            return
        if request.path.startswith("/static"):
            return
        if not session.get("user"):
            if request.path.startswith("/api"):
                return ("auth required", 401)
            return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            u = request.form.get("username", "")
            p = request.form.get("password", "")
            h = users.get(u)
            if h and check_password_hash(h, p):
                session["user"] = u
                return redirect("/")
            error = "Invalid credentials"
        return render_template_string(_LOGIN_HTML, error=error)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    return app
