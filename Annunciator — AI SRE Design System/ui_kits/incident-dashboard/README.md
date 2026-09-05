# Incident dashboard

The two views `DESIGN.md` specifies, and nothing else: a **list** of every incident (one row each) and a **detail** readout for one incident. There is no third navigation level.

## Files

| File | What it holds |
| --- | --- |
| `index.html` | The interactive shell — masthead, view switching, and the approval sequence |
| `IncidentList.jsx` | `IncidentList`, `IncidentRow` — the scannable index |
| `IncidentDetail.jsx` | `IncidentDetail`, `EvidenceRow` — the full readout |
| `data.js` | Five incident fixtures covering every status, plus the stepper labels |

## What is interactive

- **Click any row** to open its detail readout; `← ALL INCIDENTS` returns.
- **Row hover** lightens the background one step, `neutral → surface`, instantly. No lift, no transition.
- **INC-4471 is `pending_approval`** — its lamp breathes, and the approve button is present. Approving runs the real state sequence: `executing` → `verifying` → `resolved`, roughly 2.6s per step, with the pulsing dot and `restarting…` / `verifying…` copy. The stepper advances with it and confidence lands at 100%.
- **INC-4468 is `failed`** — the stepper collapses its remaining segments into one red run and the metric reads red.
- **Hover the metric value** on any detail view for the threshold tooltip.

## Composition

Every surface here is a design-system component — `Panel`, `Divider`, `StatusBadge`, `Stepper`, `DataReadout`, `MetaLabel`, `ApproveButton`, `Tooltip`. The kit adds only layout and the four screen-level pieces above; nothing is re-implemented locally.

## Provenance

`Raj-glitch-max/AISRE` is an empty repository, so there were no product screens to recreate. This kit is composed strictly from what `DESIGN.md` states — the two views, the seven statuses, the six stepper stages, the single button, the 760px centered column, the 65ch measure. Layout arrangement within those constraints is the one thing not specified in the source; if real screens exist, treat them as the correction.
