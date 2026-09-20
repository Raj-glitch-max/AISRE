# Frontend / UI changes — parked ideas

Collected while doing backend + infra work. **Nothing here is implemented.** This is a
holding file, to be worked through once the project is functionally complete.

Context: the dashboard today is a single static page (`backend/static/index.html`) served
at `/dashboard/`, polling `/incidents`, with a stepper, status badges, confidence
display, evidence list, an approve button that appears only for `pending_approval`, and a
"BREAK VICTIM-APP" demo trigger.

---

## 1. Surface the faithfulness result — the highest-value change

This is the project's actual differentiator and the dashboard currently doesn't show it
at all. The checker runs offline via `python faithfulness_eval.py <id>`; a reviewer
clicking through the UI would never know it exists.

- Render each RCA claim with its **support status inline**: a claim backed by tool
  evidence renders normally; an unsupported claim renders with a warning treatment and
  the reason (`get_container_status was never called`).
- **Incident #7 is the live proof case** — the model asserted "exit code 137 with 3
  restarts" while never calling the tool that reports either. That belongs on screen,
  not in a terminal.
- Show the flag count as a badge on the incident list row, so an unfaithful RCA is
  visible before you even open it.

## 2. Make the evidence clickable back to raw tool output

Currently `evidence` is a flat list of model-authored strings. The raw
`tool_transcript` is now persisted per incident but never displayed.

- Each evidence bullet expands to show the actual tool call (`tool`, `input`, `result`)
  it should be grounded in.
- A claim with no corresponding transcript entry visibly has nothing to expand — the
  absence becomes the tell.
- Raw transcript viewer per incident (collapsed by default, monospace, scrollable).

## 3. Show the Atlas gate as a real step, not an invisible one

The Atlas capability issue→verify→revoke cycle happens silently inside
`_gated_restart()`. To a viewer, approval just... works.

- Add a stepper stage between "approved" and "executing": *capability issued → verified →
  action authorized → revoked*.
- On failure, show *why* it was blocked (`capability rejected`, `issuance failed:
  unreachable`). The fail-closed behavior is one of the strongest things in the project
  and it's currently only observable in server logs.
- Show the scope string (`remediate:restart:{id}`) and TTL — it makes "one-shot, narrowly
  scoped" concrete instead of a claim.

## 4. Fixed-action disclosure should be prominent, not fine print

The single most important safety property — the model's `recommended_action` text is
*never executed*, only displayed — is the thing that makes a hallucinated RCA harmless.

- Visually separate "what the model recommended" (advisory, never executed) from "what
  the system will actually do" (fixed, enumerated).
- Label the recommended_action block explicitly as *not executed*.

## 5. Dashboard honesty about its own limits

In keeping with the project's pattern of documenting its own failures:

- Show the checker's measured scope/recall once it exists ("catches numeric claims about
  container state; blind to fabricated log content") directly in the UI near any flag.
- Don't let the UI imply the checker is more capable than the measurement says.

## 6. Smaller items

- Incidents #1–#4 have no `tool_transcript` (predate the feature) — render "no transcript
  recorded" rather than an empty panel.
- Timestamps are raw UTC ISO strings; show relative time ("4 min ago") with absolute on
  hover.
- Polling is unconditional; back off when no incident is active.
- No empty state for a fresh database.
- Dashboard is served from a single inline-everything HTML file — fine for now, but if
  it grows past this, split the script out.
- No error state when `/incidents` fails; it currently just stops updating silently.

## 7. Deferred / needs a decision

- Live-updating log stream during `investigating` (needs SSE or websocket; currently
  poll-only).
- A replay view that steps through an investigation round by round — strong for demos,
  meaningful build cost.
- Whether the dashboard should show AWS deployment state at all once infra lands, or
  stay purely incident-focused.
