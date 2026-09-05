# Annunciator — AI SRE Design System

Instrument-panel design system for AI SRE's incident dashboard: an agent's investigation and a human's approval, read like an aircraft caution-and-warning panel rather than a SaaS admin screen.

## Sources

| Source | What it gave us |
| --- | --- |
| `uploads/DESIGN.md` (attached by the user) | **The ground truth.** Full token set, type scale, component inventory, and written direction. Every value in this system comes from it verbatim. |
| [github.com/Raj-glitch-max/AISRE](https://github.com/Raj-glitch-max/AISRE) | **Empty repository — no commits on `main` or `master`.** No product code, screens, logos, or icons were available to read. See Caveats. |
| [github.com/fontsource/font-files](https://github.com/fontsource/font-files) | IBM Plex Mono woff2 binaries (400, 400 italic, 700) |
| [github.com/rektdeckard/departure-mono](https://github.com/rektdeckard/departure-mono) | Departure Mono woff2 / woff binaries |

If you have access to the AISRE repository, explore it directly — once it has product code, reading the real components and screens will produce far more accurate designs than working from this document alone.

## Product context

AI SRE is an incident-response system with an agent-plus-human architecture: an autonomous agent detects an anomaly, investigates, and reaches a verdict with a stated confidence — but nothing executes until a human reads the panel and approves it. The dashboard is the surface where that handoff happens.

Two views, no third navigation level:

1. **List** — every incident, one row each, scanned under mild time pressure.
2. **Detail** — one incident's full readout: status, confidence, root-cause narrative, evidence, remediation stepper, and the single approve button.

Incident states: `open`, `investigating`, `pending_approval`, `executing`, `verifying`, `resolved`, `failed`.

The design conceit and the architecture are the same shape. An annunciator light doesn't act on its own either — it tells the pilot, who acts.

## Content fundamentals

**Register.** Instrument readout, not product copy. The interface states facts and stops. There is no encouragement, no personality, no reassurance. What the user is doing is reading a gauge under time pressure, and every word either helps them decide or gets out of the way.

**The label-caps rule.** Departure Mono is capped at **roughly ten characters** — past that a pixel face stops being legible at speed, and the whole point is that it stays readable. So the uppercase micro-label role has two forms, and the length decides which: `<MetaLabel variant="caps">` for short labels (`EVIDENCE`, `CONFIDENCE`, `P95 LATENCY`, `ROOT CAUSE`), and `<MetaLabel uppercase>` — body face, +0.08em — for anything longer. `Panel`'s `label` prop applies the same switch automatically at 11 characters, so a long panel heading degrades rather than breaking the rule. Prefer shortening the label to tripping the fallback: `REMEDIATION`, not `PROPOSED REMEDIATION`.

**Casing.** Three registers, strictly separated:
- **ALL CAPS, Departure Mono, +0.15em** — status words and the button label only, and never longer than about ten characters: `OPEN`, `INVESTIGATING`, `AWAITING`, `RESOLVED`, `FAILED`, `APPROVE RESTART`.
- **Sentence case** — headlines and body prose: "Checkout latency regression", "Connection pool saturated on checkout-api after a deploy raised per-request pool checkout from one to three."
- **lower_snake_case** — machine state names when the state itself is the subject: `pending_approval`. Don't prettify these into "Pending Approval"; the raw identifier is the honest one.

**Person.** Neither "I" nor "you". The agent is referred to in the third person and by what it did — "Agent proposed a rolling restart", not "I've found the problem" or "You should restart". No first-person agent voice: a lamp doesn't talk about itself.

**Numbers.** Always exact, always with units, always tabular. `2,410 ms` not "about 2.4 seconds". `14:02:18 UTC` not "2 minutes ago" — a relative timestamp is unreadable in a postmortem. Confidence is a whole-number percentage.

**Verbs in progress use a bare present participle plus an ellipsis** — `restarting…`, `verifying…` — and only while something is genuinely happening. Nothing says "Working on it!".

**No emoji, anywhere.** No exclamation marks. No em-dash rhetoric in UI strings (this readme is prose, the interface is not). No sentence in the interface needs to be longer than about fifteen words; if it does, it belongs in the root-cause narrative panel, which is the one place actual reading happens.

**Empty and error states state the condition, not a feeling.** "No open incidents." — not "All clear, nice work!". A failed remediation reads "Health did not recover after restart." — not "Something went wrong."

## Visual foundations

**Colors.** Three signal colors, each with exactly one meaning, and nothing else permitted to use them; everything else is neutral. Amber `#f9a800` (sodium-vapor) means *this needs a human decision now* — it marks `pending_approval`, `executing`, `verifying`, plus `open` and `investigating`, and it is the fill of the one button. Yellow-green `#7fe059` (P31 phosphor) means *resolved*, nothing else; its scarcity is what makes "all clear" findable. Red `#f64258` means *remediation was attempted and health did not recover* — never a merely-open incident. Neutrals are a four-step warm-black ramp (`#0e0a07` page → `#181410` panel → `#251f1b` overlay → `#352f2a` rule), each carrying a small warm tint (OKLCH hue ~65, chroma 0.010–0.011) so it reads as a physical panel rather than a screenshot of dark mode. Metadata is warm desaturated grey `#8c857e`; reading text is warm off-white `#ebe7e4`. **Dark only — there is no light variant**, because a backlit readout only exists against a dark face.

**Type.** One face carries almost everything: IBM Plex Mono, 400 and 700 only, chosen because its humanist warmth stays legible as 13px body text. Departure Mono, a genuine pixel face, is reserved for short uppercase status labels at +0.15em. Scale runs 11 → 48px on a 1.2 ratio, hand-broken at the top so `display` jumps to 48px and reads as a gauge value rather than a heading. Tabular figures (`tnum`) on everywhere numbers appear. Line height moves inversely with size: 1.0 display, 1.2–1.25 headlines, 1.55 body, 1.4 data and captions.

**Spacing and layout.** 4px base (`xs` 4 → `xl` 32) — deliberately tighter than an 8px product scale, because density is the register. Single column, max-width 760px, **centered and symmetric** — an instrument panel's readouts align to a center console; asymmetry would fight the concept. The 760px is a layout constraint, not a reading measure: prose blocks are separately capped at `65ch` on the text element itself. Density contrasts between views — list rows use `sm`/`md` padding for scanning, detail panels use `lg` because that's where reasoning is actually read.

**Backgrounds.** Flat color, always. No imagery, no gradients, no full-bleed photography, no illustration, no repeating pattern, no texture, no grain, no scanline overlay. The warm tint in the black is the only "material" effect in the system, and it comes from the hex value itself, not from a layer on top.

**Elevation and shadow.** **No drop shadows anywhere**, inner or outer. Depth is the three-step warm-black ladder plus 1px rules. A panel sits on the page the way an instrument face sits in a console — a distinct material, not an object floating above one. Tooltips are the single exception to "everything is flat": they take the `overlay` fill, one full step brighter, because they genuinely float. There are no protection gradients and no capsules; nothing is ever placed over an image, so nothing needs protecting.

**Transparency and blur.** Effectively none. No backdrop-filter, no frosted glass, no alpha-tinted surfaces — every surface is an opaque hex from the ramp. The one legitimate use of opacity in the entire system is the `pending_approval` pulse, which animates opacity on the status label. Never use `color-mix` or an alpha channel to mute text; a dimmed signal color is a broken lamp.

**Borders.** 1px, `#352f2a`, and only as a hairline rule between list rows and panel sections. Never as a box outline. Badges and the button have no drawn border at all — their flat fill meets the background at a hard edge, and that edge is the border.

**Corner radii.** **Zero, everywhere, without exception** — declared as intentionally omitted rather than as a `none: 0` token, since there's no scale to name. One rounded card undoes the instrument read for the whole screen it's on.

**Cards.** There are none in the usual sense. The unit of grouping is `Panel`: a flat `#181410` rectangle, 20px padding, no radius, no border, no shadow. What distinguishes it from the page is one step of value, and that is the entire treatment.

**Animation.** Three cases, and nothing else. `pending_approval` breathes — the status label's opacity cycles 100% → 55% over 2.4s on a flat sine-like fade, the way an indicator lamp genuinely dims and brightens rather than blinking hard on/off. `executing` and `verifying` pulse a small 6px dot on the same cycle, paired with `restarting…` / `verifying…`. Everything else is an instant state flip: no entrance animation, no list stagger, no view transition, no hover lift. If a screen feels static, that is the design, not a gap in it. The pulse respects `prefers-reduced-motion`.

**Hover states.** One step of value, instantly, with **no transition duration at all**. A list row lightens `neutral → surface`. The button brightens its fill `#f9a800 → #ffc247`, a literal one-step-up value, not a new token. Nothing scales, lifts, gains a shadow, or changes opacity on hover.

**Press states.** Nothing. No shrink, no darken, no scale — the state change itself is the feedback, and it arrives immediately.

**Imagery.** There is none, and that is a stated position rather than a gap. If imagery is ever added, it must be cool-toned, high-contrast, and monochrome or near-monochrome so it doesn't compete with the three signal colors — but the correct answer is almost always a readout instead of a picture.

## Iconography

**The source provided no icon set, no icon font, no sprite sheet, and no SVGs** — the AISRE repository is empty, and `DESIGN.md` specifies no icon system. Nothing has been substituted from a CDN, because this direction genuinely does not want a general-purpose icon library.

What the system uses instead, and what you should use:

- **Typographic status words.** The status *is* the icon. `OPEN`, `AWAITING`, `RESOLVED`, `FAILED` in Departure Mono caps, in the signal color. This is load-bearing accessibility, not stylistic preference: green/amber/red is exactly the axis that fails for the ~8% of viewers with red/green colour vision deficiency, so the word is never optional.
- **Geometric primitives from the token set.** A 6px filled square for the activity dot. A 3px bar for a stepper segment. A 1px rule for a divider. A 10px amber bar beside the wordmark. These are `div`s with a background color, not drawings.
- **Unicode as connective tissue only** — the middle dot `·` between metadata fields, and the ellipsis `…` on in-progress verbs. Nothing else, and never a unicode character standing in for a pictogram (no `⚠`, no `✓`, no arrows-as-buttons).
- **No emoji, ever.**

If a genuine glyph need appears later, the right move is to ask for the product's own icon assets rather than to reach for Lucide or Heroicons — a stroke-icon library will not sit comfortably against a pixel face and hard-edged geometry.

## Brand mark

**There is no logo file in the sources.** Wherever a mark belongs, the brand name is set in plain type: `AI SRE` in Departure Mono caps at +0.15em, optionally with the 10px amber bar to its left, over the system name `ANNUNCIATOR`. Nothing here was drawn or reconstructed — if a real mark exists, supply the SVG and it will replace the wordmark.

## Components

Eight components, matching the `DESIGN.md` inventory exactly. No primitives were invented beyond it — no Input, Select, Tabs, Toast, or Avatar, because the source defines none and this interface needs none.

| Component | Group | What it is |
| --- | --- | --- |
| `Panel` | `components/surface/` | Flat `surface` rectangle, 20px padding, optional caps label and one action slot |
| `Divider` | `components/surface/` | 1px `border` rule between rows and sections |
| `DataReadout` | `components/readout/` | 48px gauge-scale numeric readout — the confidence percentage |
| `MetaLabel` | `components/readout/` | Warm-grey metadata text, and the caps micro-label role via `variant="caps"` |
| `StatusBadge` | `components/status/` | The annunciator lamp: status word in the signal color, with the pulse where the state calls for it |
| `Stepper` | `components/status/` | Six flush 3px segments; a failure collapses the remainder into one red run |
| `ApproveButton` | `components/controls/` | The only button in the system |
| `Tooltip` | `components/controls/` | Overlay-fill floating readout — the one non-flat surface |

Each directory holds `<Name>.jsx`, `<Name>.d.ts`, `<Name>.prompt.md`, and one `@dsCard` HTML showing its states.

## Index

- `styles.css` — the one file consumers link; `@import` lines only
- `tokens/fonts.css` — `@font-face` for both self-hosted faces
- `tokens/colors.css` — base ramp, signal colors, semantic aliases
- `tokens/typography.css` — font stacks and the eight type roles
- `tokens/spacing.css` — 4px scale, zero radius, panel/measure widths
- `tokens/motion.css` — pulse tokens and the `annunciator-pulse` keyframes
- `tokens/base.css` — page defaults and link colors
- `components/surface|readout|status|controls/` — the eight components
- `guidelines/*.card.html` — 22 specimen cards across Colors, Type, Spacing, Brand
- `ui_kits/incident-dashboard/` — the list and detail views, interactive (see its own README)
- `templates/incident-readout/` — copyable starting point for a single incident readout
- `assets/fonts/` — IBM Plex Mono (400/400i/700) and Departure Mono woff2
- `github.md` — source association and sync record
- `SKILL.md` — Agent Skills wrapper for use outside this project

## Caveats

- **`Raj-glitch-max/AISRE` is an empty repository.** Both `main` and `master` return no tree. There was no product code to read, no real screens to recreate, and no logo or icon assets to copy. Everything here is derived from `DESIGN.md`.
- **The UI kit is composed from `DESIGN.md`, not recreated from real screens.** The source states the two views, the seven statuses, the six stepper stages, the single button, the 760px column, and the 65ch measure — but not their arrangement. Layout within those constraints is the one place this system had to make a call. If real screens exist, treat them as the correction and send them over.
- Fonts were sourced from their upstream open-source repositories rather than from the product, so weights and subsets reflect Fontsource's Latin subset (IBM Plex Mono) and Departure Mono v1.500.
