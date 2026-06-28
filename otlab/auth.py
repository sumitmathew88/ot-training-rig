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

_LOGIN_HTML = """<!doctype html><meta charset=utf-8><title>Sign in</title>
<style>body{background:#0d1117;color:#c9d1d9;font-family:Consolas,monospace;
display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
.box{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:28px;width:300px}
h1{font-size:15px;letter-spacing:1px;margin:0 0 4px} .s{color:#8b949e;font-size:11px;margin-bottom:16px}
input{width:100%;margin:6px 0;padding:9px;background:#0d1117;border:1px solid #30363d;
border-radius:6px;color:#c9d1d9;font-family:inherit}
button{width:100%;margin-top:10px;padding:9px;background:#58a6ff;color:#0d1117;border:0;
border-radius:6px;font-weight:bold;cursor:pointer}
.err{color:#f85149;font-size:11px;margin-top:8px}</style>
<form class=box method=post><h1>SANTOS OT TRAINING RIG</h1>
<div class=s>Authorised users only. This is a simulation.</div>
<input name=username placeholder=Username autofocus autocomplete=username>
<input name=password type=password placeholder=Password autocomplete=current-password>
<button>Sign in</button>{% if error %}<div class=err>{{ error }}</div>{% endif %}</form>"""


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
