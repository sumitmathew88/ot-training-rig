# Hosting the OT training rig

This app is a single stateful process, not a static site. Three rules:

1. One worker only. The simulation binds OPC UA ports and holds state in
   memory. Running multiple workers/instances collides on ports and forks the
   plant state. Scale concurrent users with threads, never workers. The
   provided gunicorn.conf.py pins workers=1.
2. Put credentials in front. Auth is built in (otlab/auth.py). Configure real
   users before exposing it (below).
3. Keep the OPC ports private. The L1 OPC UA servers (4841-4843) bind to
   127.0.0.1 by default and are never published. Only the web console is
   reachable. Expose OPC only on a private VM if trainees need to point their
   own OPC client at it (see "Exposing OPC" below).

One more thing to know: there is ONE shared simulation. Every logged-in user
sees and controls the same plant. That suits instructor-led cohort training.
If you need isolated per-trainee plants, that is a larger change (a sim
instance per session, or one container per trainee) - ask and I will build it.

## Set up users

```
python3 make_user.py sumit       # enter a password, get a JSON fragment
python3 make_user.py trainee1
```

Merge the fragments into one env var:
```
OTLAB_USERS={"sumit":"pbkdf2:sha256:...","trainee1":"pbkdf2:sha256:..."}
OTLAB_SECRET=<paste a long random string>
```

If OTLAB_USERS is unset the app still will not run open: it prints a random
admin password to the logs at start-up so you can get in and then set users.

## Option A - Render (simplest managed path)

Good when you want a URL and HTTPS without managing a server. Free tier sleeps
after inactivity (about a minute to wake); a small paid instance removes that.

1. Push this folder to a GitHub repo.
2. New > Web Service > connect the repo.
3. Runtime: Docker (the Dockerfile is detected), or Python with start command
   `gunicorn -c gunicorn.conf.py run_platform:app`.
4. Instance type: pick the smallest paid instance for always-on, or free to
   trial. Do not enable autoscaling or multiple instances.
5. Environment: add OTLAB_USERS and OTLAB_SECRET. Render sets PORT for you.
6. Deploy. Open the URL, log in.

Railway and Fly.io work the same way (Docker + the same env vars). All three
are pay-as-you-go now; a single small always-on instance is a few dollars a
month. Keep it to one instance.

## Option B - Small VM (most control, allows OPC client access)

Best if trainees will connect engineering tools (UAExpert) to the simulated
PLCs, or you want it on a private network.

```
# on an Ubuntu VM
sudo apt update && sudo apt install -y python3-pip
pip3 install -r requirements.txt
export OTLAB_USERS='{"sumit":"..."}'
export OTLAB_SECRET='...'
gunicorn -c gunicorn.conf.py run_platform:app
```

Put a reverse proxy (Caddy or Nginx) in front for HTTPS, and a firewall so
only 443 is public. Run it under systemd so it restarts on reboot.

## Auth alternative - identity proxy

Instead of (or on top of) the built-in login, you can front the service with
Cloudflare Access or Tailscale. Access gives email-based SSO with no code and
is free for small teams; Tailscale keeps the whole thing on a private network
so only your devices can reach it. Either is a strong fit for an internal
training tool and avoids exposing anything to the open internet.

## Exposing OPC (advanced, VM only)

Only if trainees must connect their own OPC client:
```
export OTLAB_OPC_BIND=0.0.0.0
```
Then open ports 4841-4843 in the firewall to specific source IPs only. Note
the OPC UA endpoints here run without OPC-layer security (no certs), which is
fine on an isolated lab network but must never sit on the public internet.

## Persisting each user's work (Render disk)

Each trainee's tags and connectivity config are saved per username to a SQLite
file, so they can log out and return to their own workspace. That file lives at
OTLAB_DATA_DIR (the container defaults it to /data).

Without a disk, /data is inside the container and is wiped on every redeploy.
To make a trainee's work survive redeploys, attach a persistent disk:

1. In Render, open the service > Disks > Add Disk.
2. Name it (e.g. otlab-data), Mount path: /data, Size: 1 GB is plenty.
3. Save. Render redeploys with the disk attached.

A disk requires a paid instance (you are already on Starter) and a single
instance, which this app already is. From then on, logins keep their saved tags
and configuration across redeploys and restarts.

If you would rather not use a disk, an external Postgres (Render Postgres, or
the Supabase you already use) is the alternative durable store - ask and I will
wire it in.

## Security notes

- This is a simulation. Keep it isolated from any real OT network and never
  put real plant data, tags, or addresses into it.
- Set a strong OTLAB_SECRET and unique passwords per trainee. Rotate when a
  cohort finishes.
- The historian SQLite file is ephemeral on most managed hosts (resets on
  redeploy). That is fine for training; attach a volume if you want it kept.
- Always serve over HTTPS so credentials are not sent in clear text. Managed
  hosts do this automatically; on a VM, terminate TLS at the proxy.
```
```
