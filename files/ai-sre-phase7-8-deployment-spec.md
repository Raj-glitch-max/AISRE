# AI SRE — Phase 7+8: Deployment (AWS EC2) + README

Skipping the AWS-101 material — console navigation, security groups, key pairs, that's what the SAA cert already covers. This is the Linux/app-specific half: what's different about running *this* app on a real server versus your laptop, and the exact commands for it.

**Validated before going in this doc:** the one real code change (auto-triggering investigation) was tested against 4 scenarios — clean success, the agent crashing mid-run, a race that must not clobber an already-advanced status, and confirming the trigger never blocks the poller's own health-check loop.

---

## The one code change: auto-trigger investigation

Right now nothing calls `agent.py` except you, by hand. Fine for local testing — wrong for a server someone else might actually poke at. If a recruiter hits your `/admin/break` endpoint (or the optional trigger button at the end of this doc) and the incident just sits at `open` forever because nobody SSH'd in to run `python agent.py N`, the whole demo reads as broken.

**What does and doesn't get automated, on purpose:** investigation auto-triggers. Remediation does not — that gate staying manual is the entire point of Phase 5, and automating it away here would undo it the moment it mattered most.

### Change to `backend/poller.py`

Add near the top:
```python
import threading
from agent import investigate

logger = logging.getLogger("poller")  # you already have this; just confirming the name
```

Add this function (module-level, anywhere above `run_poller`):
```python
def _investigate_safely(incident_id):
    """Runs in its own thread. If agent.investigate() throws — NVIDIA API down,
    rate-limited, whatever — the incident must not sit at 'investigating' forever
    with nothing watching it. On a laptop you'd notice and rerun by hand; on a
    server, nobody's watching."""
    try:
        investigate(incident_id)
    except Exception as e:
        logger.error("investigation failed for incident %s: %s", incident_id, e)
        try:
            db = SessionLocal()
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            if incident and incident.status == "investigating":
                incident.status = "failed"
                db.commit()
            db.close()
        except Exception:
            logger.error("could not even mark incident %s as failed", incident_id)
```

Then, right after the existing line that creates the incident (`logger.error("INCIDENT CREATED: id=%s", incident.id)`), add exactly one line:
```python
threading.Thread(target=_investigate_safely, args=(incident.id,), daemon=True).start()
```

That's the entire change. `.start()` returns immediately — the poller's own 5-second health-check loop is never blocked while the agent spends 10-30 seconds calling NVIDIA.

**Test this locally before touching AWS.** Break victim-app, don't run `agent.py` yourself this time, just watch — the incident should walk itself from `open` through `pending_approval` with zero manual commands. That's the actual bar for "ready to deploy," not just "the code compiles."

---

## Part A — EC2, briefly

- **Instance**: `t3.micro` (1 GB RAM) is genuinely enough for this — Docker daemon, one alpine container, one Python process, Caddy, total footprint is a few hundred MB. If your AWS account is under 12 months old, this is free-tier eligible; either way it's a few dollars a month at worst.
- **Elastic IP** — allocate one and associate it with the instance. A plain public IP changes on stop/start, which will silently break your DNS record later. Free while attached to a running instance.
- **Security group**: inbound 22 (SSH, restrict to your IP if you want), 80, 443. **Not** 8000 or 9000 — victim-app and the backend both stay internal-only, reached only via localhost on the box itself. Caddy is the only thing the internet ever touches.
- **AMI**: Ubuntu 24.04 LTS.
- **Domain**: you already own `rajpatil.dev` — use a subdomain (`sre.rajpatil.dev` or similar) rather than a bare IP or the default `ec2-x-x-x-x.compute.amazonaws.com` hostname. Point an A record at the Elastic IP. If you're managing this through Cloudflare like Atlas, set this specific record to **DNS-only (grey cloud)**, not proxied — Cloudflare's proxy will interfere with Caddy's automatic Let's Encrypt certificate issuance unless you set up DNS-01 challenges, which is unnecessary complexity for what this needs.

---

## Part B — Server setup

SSH in, then:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3.12-venv ca-certificates curl gnupg
```

**Docker** (the official repo, not the quick-install script — this is the machine your resume link runs on, not a throwaway):
```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
sudo usermod -aG docker $USER
newgrp docker
```

**Caddy** (official repo):
```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

---

## Part C — Get the code on, set up the secret properly

```bash
git clone https://github.com/Raj-glitch-max/AISRE.git
cd AISRE/victim-app
docker build -t victim-app .
docker run -d --restart unless-stopped -p 127.0.0.1:8000:8000 --name victim-app victim-app
```

Note `127.0.0.1:8000:8000`, not `8000:8000` — victim-app binds to loopback only. It should never be reachable from outside this box.

```bash
cd ../backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**The NVIDIA key** — same rule as always, not in the repo, not in a systemd unit file that might get `cat`'d by something. A dedicated env file with locked-down permissions:
```bash
sudo mkdir -p /etc/ai-sre
sudo tee /etc/ai-sre/backend.env > /dev/null << 'EOF'
NVIDIA_API_KEY=your-real-key-here
EOF
sudo chmod 600 /etc/ai-sre/backend.env
sudo chown $USER:$USER /etc/ai-sre/backend.env
```

---

## Part D — Run it persistently (systemd, not a terminal you can't close)

```bash
sudo tee /etc/systemd/system/ai-sre-backend.service > /dev/null << 'EOF'
[Unit]
Description=AI SRE backend
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/AISRE/backend
EnvironmentFile=/etc/ai-sre/backend.env
ExecStart=/home/ubuntu/AISRE/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 9000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ai-sre-backend
sudo systemctl status ai-sre-backend
```

**One easy-to-miss gotcha: no `--workers` flag, ever, on this app specifically.** The poller runs as an in-process background thread started at app startup. Two uvicorn workers means two independent poller threads, each with its own `active_incident_id` tracking, both racing to create incidents off the same `/health` checks — the exact duplicate-incident bug from Phase 1, reintroduced by a deployment flag that looks like a harmless performance tweak. One worker, always, for this specific app.

`--reload` is also gone (it was a dev convenience, not something you want auto-restarting a live process on file changes that shouldn't happen on a stable server anyway).

---

## Part E — Caddy: the whole reverse proxy config

```bash
sudo tee /etc/caddy/Caddyfile > /dev/null << 'EOF'
sre.rajpatil.dev {
    reverse_proxy 127.0.0.1:9000
}
EOF

sudo systemctl reload caddy
```

That's genuinely the entire file. Caddy provisions and renews the Let's Encrypt certificate automatically the first time it sees a request for that domain — no certbot, no manual renewal cron job, no separate TLS config. This is the actual reason Caddy over nginx here: nginx would need a separate certbot setup and a renewal timer; Caddy does both in three lines.

---

## Part F — End-to-end verification, on the real server, not localhost

```bash
# from your own machine, not the server
curl https://sre.rajpatil.dev/incidents
# [] or your existing incidents — either way, a real HTTPS response, not a cert warning

curl -X POST https://sre.rajpatil.dev/incidents  # this should 405, not 500 — confirms routing is real, not a fluke
```

Then the actual test: hit the dashboard in a browser at `https://sre.rajpatil.dev/dashboard/`, and this time trigger the break from the server side directly (since victim-app's admin endpoints are loopback-only and correctly not reachable from your laptop — that's the security boundary working, not a bug):

```bash
# on the server
curl -X POST localhost:8000/admin/break
```

Watch the dashboard **without touching anything else** — no SSH session running `agent.py`, no manual step. If it walks itself from OPEN to AWAITING on its own, the auto-trigger is confirmed working in the actual deployed environment, not just in a local test.

---

## Troubleshooting: what's different about a server vs. your laptop

| Problem | Fix |
|---|---|
| `curl https://sre.rajpatil.dev` hangs or times out | DNS hasn't propagated yet, or the security group is missing 443. Check `dig sre.rajpatil.dev` resolves to your Elastic IP first |
| Caddy fails to get a certificate | Almost always port 80 blocked in the security group — Let's Encrypt's HTTP-01 challenge needs it open, even though the final traffic is all 443 |
| Backend service won't start, `journalctl -u ai-sre-backend` shows `ModuleNotFoundError` | `ExecStart` is pointing at the venv's python indirectly via uvicorn — confirm the venv path in the unit file matches exactly where you actually created it |
| Incidents duplicate rapidly right after deploying | Check `ExecStart` doesn't have a stray `--workers 2` or similar — see Part D |
| `docker run` for victim-app fails with "port already allocated" on a redeploy | `docker rm -f victim-app` first, same as it always has locally |
| Dashboard loads but fonts look like fallback system fonts | `backend/static/fonts/` didn't make it in the `git clone` — check it's actually committed, not gitignored by accident |

---

## Optional, not required: a trigger button instead of curl

A technical recruiter is fine running a curl command; a non-technical one isn't. If you want the dashboard to be a fully self-contained demo, add one backend endpoint that proxies the break/fix admin calls (keeping victim-app itself loopback-only, not exposing it directly):

```python
import httpx

@app.post("/demo/trigger-incident")
def demo_trigger():
    httpx.post("http://localhost:8000/admin/break", timeout=3)
    return {"status": "triggered"}
```

Then a small button in `index.html` calling `fetch("/demo/trigger-incident", {method: "POST"})`. Genuinely optional — the project is complete and demoable without it. Mentioning it here rather than building it now so it doesn't become one more thing standing between you and actually shipping this.

---

## Reporting back

- **Dashboard reachable over HTTPS at your real domain, auto-trigger confirmed working live → say "Phase 7 done."** README is the very last piece, in the next file.
- **Something breaks and it's in the table → fix it, keep going.**
- **Something breaks and it's not in the table → paste exactly:** the command, the full output, `journalctl -u ai-sre-backend -n 50` if the backend's involved, what you expected.
