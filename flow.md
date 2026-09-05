# Flow log — Phase 0, 1, 2, 3, 4

## Starting state (before any of this)

The runbook assumed a folder layout of `ai-sre/victim-app/` + `ai-sre/backend/` with
file contents already sitting in a spec doc. Neither was true on disk:

- `victim_app/` (underscore) already existed, but it's not a scratch project — it's a
  real, separate GitHub repo called **atlas** (`Raj-glitch-max/atlas`, clean tree,
  tracking `origin/main`, 25+ merged PRs). It's a certificate issuance/revocation
  system with no relation to the `/health` / `/orders` / `/admin/break` toy app the
  runbook describes.
- `backend/` existed but was empty except for an unpopulated `venv/`.
- No spec doc with the actual source could be found on the filesystem or in connected
  Google Drive.

**Decision:** leave `victim_app/` (the real atlas repo) untouched, and build the toy
app fresh in a new `victim-app/` (hyphen) folder — which is also the exact name the
runbook itself uses. `backend/` was populated in place since it was already empty.
This was confirmed with the user before writing any code.

## Phase 0 — victim-app

### What was built

`victim-app/main.py` — FastAPI app with exactly the four endpoints the runbook
checks, nothing else (per "don't add anything the spec didn't ask for"):

- `GET /health` — returns `{"status": "healthy"}`, or 500 `dependency unavailable`
  when broken.
- `GET /orders` — returns a 2-item hardcoded order list, or 500 `connection refused`
  when broken.
- `POST /admin/break` / `POST /admin/fix` — flip a module-level `is_broken` flag.

Every handler calls `logger.info(...)` on the healthy path and `logger.error(...)`
on the broken path *before* raising `HTTPException`, so `docker logs` gets an
unambiguous INFO/ERROR split regardless of how uvicorn's own access logging is
configured — this is what row 6 checks for.

`Dockerfile` + `requirements.txt` + `.gitignore` / `.dockerignore` round out the repo.

### Failure: Docker build failed TLS verification (not in the runbook's table)

```
docker build -t victim-app .
→ x509: certificate has expired or is not yet valid:
  current time 2026-09-04T23:31:27+05:30 is before 2026-09-05T00:51:31Z
```

This isn't one of the anticipated row-2 failures (wrong folder, pip typo). Diagnosis:

```
timedatectl status
→ System clock synchronized: no
  NTP service: active   (systemd-timesyncd running but stuck at "Idle")
```

The host clock was running behind real time, so Docker Hub's registry cert (issued
very recently) looked "not yet valid" from the client's point of view. This isn't
specific to this task — it would break any strict TLS validation on the box until
fixed.

Two paths existed: fix the clock (needs sudo, which wasn't available
non-interactively — `sudo -n true` failed), or route around the registry pull
entirely. `docker images` showed `python:3.12-alpine` already cached locally (from
unrelated prior work), so the fix was:

- `Dockerfile`: `FROM python:3.12-slim` → `FROM python:3.12-alpine` (already cached,
  no registry pull needed).
- `requirements.txt`: `uvicorn[standard]` → `uvicorn` (plain). Alpine uses musl libc,
  not glibc; the `[standard]` extra pulls in uvloop/httptools which are C extensions
  that may not have musl wheels. Plain `uvicorn` is pure Python (click + h11), so it
  installs cleanly on alpine with zero risk of a compiler-toolchain error. In the
  end pydantic-core *did* have a prebuilt musllinux wheel available, so this was a
  conservative choice rather than a strictly necessary one — but it avoided
  introducing a second unknown failure mode while already debugging one.

The user's system clock is still unsynced as of this writing (fixing it needs a
password we don't have) — flagging in case it causes trouble elsewhere later.

### Verification (all rows matched)

| Row | Command | Result |
|---|---|---|
| 1 | `git init && git add . && git commit` | Clean commit, 5 files |
| 2 | `docker build -t victim-app .` (alpine) | Built cleanly |
| 3 | `docker run -d -p 8000:8000 --name victim-app victim-app` | Container ID printed |
| 4 | `curl /health`, `curl /orders` | `{"status":"healthy"}`, 2-item list |
| 5 | `POST /admin/break` then health/orders | Both 500, `dependency unavailable` / `connection refused` |
| 6 | `docker logs victim-app` | Clean INFO→ERROR split at the break point |
| 7 | `POST /admin/fix` then health | Back to `{"status":"healthy"}` |

The Dockerfile/requirements fix was committed separately after verification
(`fix: use alpine base + plain uvicorn to avoid registry TLS clock issue`), keeping
row 1's "clean commit" intact as the actual first commit.

## Phase 1 — health poller + incident model

### What was built

- `backend/database.py` — SQLAlchemy engine/session against `sqlite:///./incidents.db`.
- `backend/models.py` — `Incident(id, status, opened_at, resolved_at)`. Uses
  `default=datetime.utcnow` (not `datetime.now(timezone.utc)`) deliberately — this
  matches the runbook's own "expected noise" note about the `datetime.utcnow()`
  deprecation warning on Python 3.12, so seeing that warning is confirmation of
  correct behavior, not a bug.
- `backend/poller.py` — `run_poller()`: polls `TARGET_URL = "http://localhost:8000/health"`
  every 5s via `httpx.AsyncClient`. On failure, opens a new incident **only if**
  `active_incident_id is None` — this check is nested strictly inside the
  `if not healthy:` branch (poller.py:33-41). The runbook calls out an indentation
  slip that hoists this guard out of the failure branch as "the single most common
  bug in this file," so this nesting was re-read line-by-line against the spec
  before moving on. On success, a `consecutive_successes` counter increments and
  resolves the open incident once it reaches 2.
- `backend/main.py` — `GET /incidents`, and starts the poller via
  `@app.on_event("startup")`. This is the deprecated-but-functional style the
  runbook's other "expected noise" note references (FastAPI 0.115.0 still runs it
  fine) — used deliberately, not by accident.

### Failure: none outside the runbook

`pip install` had a couple of transient `Connection refused` retries against PyPI
at the very start, which pip retried automatically and then succeeded — not the
clock issue (PyPI's certs weren't in the affected window), just a momentary network
hiccup. No action needed.

### Verification (all rows matched, with log evidence)

| Row | Command | Result |
|---|---|---|
| 1 | `pip install -r requirements.txt` | Installed cleanly |
| 2 | `uvicorn main:app --reload --port 9000` | Running on :9000, poller hitting `/health` every 5s |
| 3 | `curl :9000/incidents` (healthy) | `[]` |
| 4 | break victim-app, wait 13s, `curl :9000/incidents` | Exactly 1 incident, `"status":"open"` |
| 5 | fix victim-app, wait 14s, `curl :9000/incidents` | Same incident, `"status":"resolved"`, `resolved_at` populated |

Backend log timeline for the break→fix cycle, confirming the guard held across
repeated failures and resolution required exactly 2 consecutive successes:

```
23:40:57  GET /health → 500          ERROR Incident 1 opened: victim-app unhealthy
23:41:02  GET /health → 500          (no new incident — guard held)
23:41:07  GET /health → 500          (no new incident — guard held)
23:41:12  GET /health → 500          (no new incident — guard held)
23:41:17  GET /health → 500          (no new incident — guard held)
23:41:22  GET /health → 200          (1st consecutive success)
23:41:27  GET /health → 200          (2nd consecutive success)  INFO Incident 1 resolved
```

## Interlude — mid-session service restart

Between Phase 1 and Phase 2 the `victim-app` container exited (255) and the backend
uvicorn process died — evidence pointed to a Docker daemon or machine restart in the
background (container `CREATED 18h ago`, `Exited 14h ago` when checked). Both were
simply restarted (`docker start victim-app`; re-launch `uvicorn main:app --reload
--port 9000`) — the SQLite file had persisted, so incident #1's resolved record came
back intact with no data loss. No code changes needed.

Also flagged separately: an attempt to fix the earlier clock-sync issue via
`apt install chrony` failed (the network couldn't reach most apt mirrors — DNS was
returning the local gateway IP for many hostnames, and one request got redirected to
a router login page, consistent with an intermittent captive-portal-style network
rather than a clean outage). That attempt left `systemd-timesyncd` stopped (though
still installed) with no replacement running. This is noted but not fixed — it
doesn't block anything in this project, since all package installs here go through
PyPI directly (unaffected) rather than Docker Hub or apt.

## Phase 2 — SRE tools (`backend/tools.py`)

Three plain Python functions, no model involvement:

- `get_container_status(container_name)` — `docker inspect`, returns running state,
  exit code, restart count, start time.
- `get_recent_logs(container_name, lines)` — `docker logs --tail N`, stdout+stderr
  combined.
- `get_recent_commits(repo_path, count)` — `git log` against `victim-app/` (the repo
  git-init'd in Phase 0), parsed into structured `{hash, author, date, message}` dicts.

All three return structured dicts/strings/lists rather than raising — errors (docker
not found, container missing, not a git repo) come back as `{"error": "..."}` so the
agent loop always gets *something* parseable instead of a crash.

**Verification:** `python tools.py` standalone — all three returned real data
(`running: True`, actual victim-app log lines, the two Phase-0 commits from
`victim-app/`'s git history). No model involved at this stage, per the spec's
instruction not to wire tools to the model until each works standalone.

## Phase 3 — NVIDIA NIM agent loop (`backend/agent.py`)

### Provider swap

Per spec, this build uses NVIDIA NIM's OpenAI-compatible endpoint
(`https://integrate.api.nvidia.com/v1`) via the standard `openai` Python package
instead of the Anthropic SDK. No `ANTHROPIC_API_KEY` / `anthropic` package anywhere
in this project.

The key itself was shared directly in chat (a development key the user says they
manage/rotate). It was **not** written into any source file — `agent.py` and
`nim_test.py` both read it from `os.environ["NVIDIA_API_KEY"]`, matching the spec's
own instruction ("Do NOT put the key directly inside Python code").

### Failure: the spec's default model (`deepseek-ai/deepseek-v4-pro-0813`) doesn't work on this account

`GET /v1/models` confirmed the key is valid and that model is listed in NVIDIA's
general catalog. But every `POST /chat/completions` call against it hung completely
— no response, not even an error, for 100+ seconds (verified twice, once via the
Python client, once via raw `curl --max-time 100`). This is different from a normal
failure mode:

- A genuinely unavailable/unprovisioned model returns a **fast 404**
  (`"Function '...' Not Found for account '...'"` — confirmed with
  `google/gemma-2b` and `mistralai/mistral-7b-instruct-v0.3`, both instant).
  So the hang isn't "model not entitled."
- A busy model returns a **fast 503** (`"Service temporarily overloaded"` — this is
  exactly what `nvidia/nemotron-3-ultra-550b-a55b` returned on its first attempt, in
  under 24s, then succeeded on retry).

`deepseek-ai/deepseek-v4-pro-0813` did neither — it just never responded. That looks
like a broken/stuck backing deployment on NVIDIA's side for this specific model on
this account, not something fixable from this end.

**Fix:** switched the default model (both `nim_test.py` and `agent.py`) to
`nvidia/nemotron-3-ultra-550b-a55b` — the model the user's own working example used.
Verified independently before touching the agent:
1. Plain chat completion — real response, ~20s.
2. Tool-calling with `tool_choice: "required"` — correct `tool_calls` array,
   correct function name/arguments, `finish_reason: "tool_calls"`.

The model stays fully configurable via `NIM_MODEL` env var exactly as the spec
requires, so switching again later (e.g. if NVIDIA fixes the deepseek endpoint, or
changes the free catalog) is a one-line change, not a code change.

### Agent loop implementation

`agent.py` matches the spec's design as given:

- Round 1 forces `tool_choice: "required"`; later rounds use `"auto"`.
- Assistant messages round-tripped via `message.model_dump(exclude_none=True)` so
  tool-call history stays intact across rounds.
- `executed_tool_count` is tracked in Python, independently of what the system
  prompt asks for — the agent will not accept a final RCA below 2 executed tools,
  regardless of what the model claims. This is the "program-level enforcement, not
  just prompt-level" the spec calls out.
- `MAX_ROUNDS = 5` caps runaway loops; hitting the cap without a valid RCA sets
  `status = "failed"` rather than looping forever.
- JSON parsing tolerates ```json fences the model might wrap around its answer.

One necessary addition beyond the literal spec: `backend/main.py`'s `GET /incidents`
handler only serialized the original 4 fields (`id`, `status`, `opened_at`,
`resolved_at`). It was updated to also return `service_name`, `root_cause`,
`confidence`, `evidence` (JSON-decoded back into a list), `recommended_action`, and
`risk` — otherwise the RCA would be persisted in SQLite but invisible through the
API, which the spec's own completion criteria require checking via `curl`.

## Phase 4 — structured RCA + persistence

### Migration (`backend/migrate_db.py`)

Added `service_name, root_cause, confidence, evidence, recommended_action, risk` via
idempotent `ALTER TABLE ... ADD COLUMN` (skips columns that already exist), rather
than `create_all()` (which only creates missing *tables*, not missing *columns* on
an existing table) or dropping `incidents.db` (which would have thrown away
incident #1 from Phase 1 testing). Ran once, verified via
`inspect(engine).get_columns("incidents")` — all 10 columns present, incident #1's
row untouched.

### End-to-end run (incident #2)

1. `POST /admin/break` → Phase 1 poller opened incident #2 (`status: "open"`)
   ~5s later, exactly as in Phase 1.
2. `python agent.py 2`:
   - Round 1: model requested all three tools in a single response (valid parallel
     tool-calling — `get_container_status`, `get_recent_logs`, `get_recent_commits`
     all executed, `executed_tool_count = 3`).
   - Round 2: model returned a valid structured RCA directly (no more tools needed).
   - RCA correctly identified `/admin/break` itself as the root cause by correlating
     the admin log line with the subsequent health failures — confidence 0.95,
     risk `medium`.
3. `GET /incidents` confirmed the RCA fields were persisted in SQLite (not just
   printed to the terminal) and `status` was `pending_approval`.
4. `POST /admin/fix` → waited ~14s → `GET /incidents` showed incident #2 as
   `status: "resolved"`, `resolved_at` populated. This is Phase 1's poller acting
   independently of the agent (its own in-memory `active_incident_id` guard doesn't
   know or care about the agent's `pending_approval` status) — and it correctly
   flipped only `status`/`resolved_at`, leaving all the RCA fields the agent wrote
   untouched. This is the state-machine handoff the spec describes
   (`open → investigating → pending_approval`, then Phase 1 independently drives
   `→ resolved`), and it worked without any glue code between the two systems.

### Completion criteria (Part L) — all satisfied

Every item in the spec's checklist was verified directly against real output during
this run: Phase 0/1 still work, RCA fields exist and migrated cleanly, the NVIDIA
key and (substituted) model work, all three tools work standalone and via the
agent, at least 2 tools were executed (3, in fact), the RCA is schema-valid and
persisted, and the incident correctly reached `pending_approval` then `resolved`.

**Phase 2+3+4 done.**

## Phase 5 — remediation + verification (`backend/remediation.py`)

### What it does

`approve_and_remediate(incident_id)` drives `pending_approval → executing →
verifying → resolved | failed`:

1. Re-checks the incident is `pending_approval`, else raises
   `IncidentNotPendingApproval`.
2. `docker restart victim-app`. This genuinely fixes the toy system because the
   broken state is a single in-memory Python flag — restarting the process resets it
   to its code default, the same reason "turn it off and on again" actually works on
   real transient/stateful bugs.
3. Waits `VERIFY_WAIT_SECONDS = 8`, then re-checks `/health` up to 3 times at 3s
   intervals.
4. `resolved` + `resolved_at` if health came back; `failed` otherwise. A failed
   restart short-circuits to `failed` and never reaches verification.

**What it deliberately does not do:** it never executes the agent's free-text
`recommended_action`. The action is fixed and predetermined — a container restart.
The human approves "restart the service given this diagnosis," not "run whatever the
model suggested." This turned out to matter in practice — see the hallucination note
below.

### Deviations from the spec's code, and why

- `from db import SessionLocal` → `from database import SessionLocal` (this project's
  module is `database.py`).
- `import requests` → `httpx`. The spec claimed `requests` was already in the Phase 1
  `requirements.txt`; it isn't — this project uses `httpx`, which is already a
  dependency and has an equivalent sync API. Adding `requests` would have meant a new
  dependency for no gain.
- `main.py`'s endpoint uses `SessionLocal()` directly rather than the spec's
  `db: Session = Depends(get_db)` — this project has no `get_db` dependency, and
  matching the existing style beat inventing one.
- `StaticFiles(directory="static")` → an absolute path derived from `__file__`. A
  relative path breaks whenever uvicorn is started from any directory other than
  `backend/`.

### The synchronous guard (the spec's load-bearing point)

The `pending_approval` check lives in the *endpoint*, before
`background_tasks.add_task(...)`. `BackgroundTasks` runs after the response is
already sent, so a guard living only inside `approve_and_remediate` would return
`{"status": "approval received"}` to an invalid request and surface the rejection
nowhere but the server log. Verified directly:

| Request | Result |
|---|---|
| `POST /incidents/1/approve` (already `resolved`) | **409** `incident is not pending approval (status: resolved)` |
| `POST /incidents/999/approve` (nonexistent) | **404** `incident not found` |
| `POST /incidents/3/approve` (genuinely pending) | **200** `approval received, remediation started` |

### End-to-end remediation run (incident #3)

victim-app was broken and **deliberately never fixed by hand** — the restart had to
be what fixed it, or the test would prove nothing.

```
[incident 3] status -> executing
[incident 3] status -> verifying
[incident 3] status -> resolved (verified healthy)
```

`GET /incidents` then showed `status: resolved` with `resolved_at` populated, and
`GET :8000/health` returned `{"status":"healthy"}` — confirming the container restart
genuinely cleared the in-memory flag rather than the DB just claiming success.

## Phase 6 — dashboard (`backend/static/`)

### Starting point: the design was a prototype, not an app

The existing `Annunciator — AI SRE Design System/ui_kits/incident-dashboard/` is a
Claude Design export. It looks right, but it was not wired to anything:

- It read a hardcoded `window.INCIDENTS` array from `data.js` (fake incidents for
  `checkout-api`, `auth-gateway`, etc.), never the real `/incidents` API.
- Its approve handler was `advance()` — a `setTimeout` chain that faked
  `executing → verifying → resolved` locally. No HTTP request at all.
- It loaded React, ReactDOM and Babel-standalone from `unpkg.com` and transpiled JSX
  in the browser on every page load.

### What was built instead

`backend/static/index.html` — a single self-contained page, vanilla JS, no build
step and no CDN, wired to the real API. The Annunciator design language is preserved
exactly: the tokens (`tokens.css`) and the five self-hosted woff2/woff faces are
vendored from the design export, with `@font-face` URLs rewritten to `./fonts/`.

The CDN was dropped deliberately: this machine's network has been intermittent all
along (it broke the Docker registry pull in Phase 0 and an `apt` run later), and a
dashboard that silently renders nothing when unpkg is unreachable is not a dashboard.
Self-hosting the fonts and dropping React removes every runtime network dependency
except the app's own API.

Design fidelity notes — the components were ported, not approximated: `StatusBadge`
stays a coloured *word* rather than a filled pill, `Panel` has no radius and no
shadow, `Divider` is a 1px rule, `Stepper` is six flush segments where a failed run
replaces the remainder with one red segment, `DataReadout` keeps the 48px display
figure with the half-size unit, and `ApproveButton` is the single sodium-amber fill
in the whole page.

Where real data forced a change from the mock:

- Mock evidence was `[label, value]` pairs; real evidence is a flat list of strings,
  so the two-column grid became single-column rows keeping the same hairline rhythm.
- The mock's `metric` block (p95 latency, queue depth) has no real equivalent. Rather
  than invent a fake metric, that slot shows the real `risk` field next to confidence.
- Real statuses map onto the six-step bar as
  `open→0, investigating→2, pending_approval→3, executing→4, verifying→5, resolved→6`.

Two things added that the prototype had no need for:

- **HTML escaping.** JSX escaped interpolated values automatically; building strings
  for `innerHTML` does not. `root_cause` and `evidence` are model output, so
  everything is passed through `esc()` first.
- **The 409 path.** The prototype had no failure branch because it never made a
  request. If approval is rejected the button now shows `REJECTED` and prints the
  server's reason.

### Verification (no browser available)

The Chrome extension was not connected, so **the dashboard was not visually confirmed
in a browser** — this is the one item in this phase not verified the way the spec's
Part D Part 2 describes. In its place, the real script was extracted from the served
page and exercised in Node:

- `dash_test.js` — 65 assertions over the pure logic: status vocabulary for all seven
  statuses, the polling gate, stepper geometry (including the failed branch and the
  all-done resolved case), confidence formatting, badge markup, and XSS escaping.
- `render_test.js` — 43 assertions feeding the **live `/incidents` payload** through
  the real `renderList`/`renderDetail`, checking each incident renders its badge,
  stepper, confidence, risk and full evidence list, that the approve button appears
  for `pending_approval` and *only* then, and that the fixed-action disclosure is
  always present.

All assets serve correctly over HTTP: `/dashboard/` 200 (18.3 KB), `tokens.css` 200,
woff2 200.

### A real finding: the model hallucinated an RCA

Incident #3's RCA claimed the container was being OOM-killed — "exit code 137",
"3 restarts", "connection reset by peer" — none of which appear in the tool output.
`get_container_status` had returned `restart_count: 0`, `exit_code: 0`,
`status: running`. The model fabricated a plausible-sounding story around the one
real signal it had (the recent alpine commit).

This is a model-quality issue, not a pipeline bug — the loop gathered real evidence,
enforced the 2-tool minimum, produced schema-valid JSON and persisted it correctly.
Incident #4, same code, produced an accurate RCA. It is worth recording because it
validates the Phase 5 design decision above: because remediation executes a fixed
action and never the model's `recommended_action` text, a hallucinated RCA could not
cause a wrong action to be taken. The blast radius of a bad diagnosis is a wrong
*explanation*, not a wrong *action*.

## Repository state

The AISRE root is a git repo tracking `github.com/Raj-glitch-max/AISRE.git`. Two
problems were found in what had been committed:

1. **The venv was in the repo.** 5,868 of 5,885 tracked files were `backend/venv/`,
   plus 2,800 `__pycache__` entries and the runtime `incidents.db`. Untracked via
   `git rm -r --cached` (files untouched on disk) and a real `.gitignore` added — the
   previous one was 0 bytes. The repo now tracks 11 source files plus the design
   system.
2. **`victim-app/` was committed as a gitlink, not as files.** It had its own `.git`
   (from Phase 0, where the runbook required it for the commit-history tool), so the
   parent repo stored it as mode `160000` pointing at commit `59d7e7c` — with no
   `.gitmodules`. Anyone cloning AISRE.git got an empty `victim-app/` directory,
   making the project non-functional from a fresh clone.

   **Fixed via `git subtree add`**, which imports the files *and* the history rather
   than just copying the files in: victim-app's two original commits (`0d57b89`,
   `59d7e7c`) are now reachable inside AISRE's history, and the nested `.git` is
   gone. A submodule was considered and rejected — it would have kept victim-app
   independently versioned at the cost of a second repo and a
   `git clone --recursive` footgun for anyone browsing the project.

   The agent's `get_recent_commits` tool still works: with no nested `.git`, `git log`
   from `victim-app/` resolves to the parent repo, which now carries both victim-app's
   original commits and the ongoing project history. Verified after the change.

   A fresh `git clone` was then run end-to-end to confirm the repo is actually
   usable: victim-app source, all nine backend modules, and the dashboard (with
   fonts and tokens) all present; `venv/` and `incidents.db` correctly absent.

## Independent confirmation: the dashboard actually works in a browser

Between the last update and this one, three real screenshots arrived
(`files/dashboard-{list,detail,resolved}.png`, now copied to `docs/`) showing the
dashboard running at `localhost:9000/dashboard/` in an actual browser — the list view
with the live AWAITING count, the detail view with stepper/confidence/risk/evidence
rendering correctly, and the resolved state with "Verified healthy at 20:14:47 UTC."
This closes the gap flagged at the end of Phase 6: the Chrome extension was never
connected in this session, so the dashboard's *visual* correctness had only been
inferred from 108 Node assertions, never actually seen. It's now confirmed working,
just not by me directly.

## Phase 7 (partial) — auto-trigger investigation

### The one code change

Per spec: `backend/poller.py` now starts `agent.investigate()` in a daemon thread
immediately after opening an incident, so nobody has to SSH in and run `python
agent.py N` by hand. `_investigate_safely()` wraps the call — if `investigate()`
throws (NVIDIA down, rate-limited), the incident is marked `failed` instead of
sitting at `investigating` forever with nothing watching it.

### A regression the spec didn't anticipate, found and fixed before it shipped

`agent.py` built its `OpenAI` client at **import time**
(`client = OpenAI(api_key=os.environ["NVIDIA_API_KEY"])`, module level). Once
`poller.py` imports `investigate` — and `main.py` always imports `poller.py` — a
missing `NVIDIA_API_KEY` now crashed the **entire app** on startup, not just the
investigation path. Confirmed directly:

```
$ unset NVIDIA_API_KEY && python -c "import main"
KeyError: 'NVIDIA_API_KEY'
```

This is a real problem for exactly the deployment scenario Part D describes: a typo
in `/etc/ai-sre/backend.env`'s path, or the file missing its permissions, would
crash-loop the *whole service* — no dashboard, no `/incidents`, no Phase 1 health
monitoring at all — rather than degrading gracefully to "the poller and dashboard
work, investigations just fail." Fixed with a lazy client (`_get_client()`,
instantiated on first use, not at import). Re-verified the same test now imports
clean without the key, and that `_investigate_safely`'s existing try/except still
catches a missing-key failure and marks the incident `failed` correctly.

### End-to-end verification, exactly as the spec's own bar requires

"Test this locally before touching AWS... the incident should walk itself from
`open` through `pending_approval` with zero manual commands." Broke victim-app,
touched nothing else:

```
open -> investigating (immediately)
... 85 seconds, zero manual intervention ...
investigating -> pending_approval
```

Confirmed the poller's own 5-second health-check loop never stalled during the
85-second investigation — log timestamps stayed exactly 5.00-5.04s apart throughout,
proving the background thread genuinely didn't block the event loop. Approved the
resulting incident (#5) and the full remediation cycle completed normally
(`executing -> verifying -> resolved`, `/health` genuinely healthy afterward).

### Optional demo-trigger endpoint — built, not skipped

The spec marks `POST /demo/trigger-incident` as optional ("genuinely optional — the
project is complete and demoable without it"). Built it anyway, plus the button the
spec only described in passing ("a small button in `index.html`"), because half of a
feature — a backend endpoint a recruiter has no way to actually click — isn't a
complete demo path. The button (`BREAK VICTIM-APP`, top-right of the masthead) is
deliberately a quiet outlined ghost button, never the amber fill — that fill is
reserved for the approve action alone, per the design system's own stated rule.
Verified: clicking triggers a real `/admin/break`, the poller and auto-trigger take
it from there exactly as the manual `curl` path does (incident #6, confirmed
`investigating` within 5s of the click).

### What Phase 7 still needs, and why it's paused here

Everything above is local code, fully verified. The rest of Phase 7 — provisioning
an EC2 instance, an Elastic IP, security groups, DNS for `sre.rajpatil.dev`, Caddy,
and a systemd unit — requires AWS console/CLI access, SSH access to a real server,
and DNS control, none of which this environment has. That work is paused pending a
decision on how to proceed (this session has no path to provision or reach a real
server on its own).

The README supplied in `files/README.md` states `**Live:** https://sre.rajpatil.dev/
dashboard/` and a publicly-curlable `/demo/trigger-incident` — neither is true yet.
It has **not** been copied into the repo root as-is, to avoid committing a false
claim; the screenshots it references have been staged in `docs/` since they're
accurate regardless of deployment status.

## Current running state

- `victim-app` Docker container: running.
- Backend uvicorn: running (`--reload`, port 9000), poller active (now with
  auto-trigger), dashboard served at `http://localhost:9000/dashboard/`, including
  the new BREAK VICTIM-APP button.
- `incidents.db` has 6 rows: #1–#5 resolved, **#6 mid-investigation** (opened via the
  new demo-trigger endpoint during this verification pass).
- `NVIDIA_API_KEY` is not persisted in any project file — export it in-shell before
  starting the backend now (not just before running `agent.py` — see the lazy-client
  fix above for why that distinction now matters).

Next: **finish Phase 7 (actual AWS deployment — needs access this session doesn't
have) + Phase 8 (README, once its live-URL claim is either true or removed).**
