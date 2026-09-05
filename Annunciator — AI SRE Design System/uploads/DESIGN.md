---
version: alpha
name: Annunciator
description: Instrument-panel design system for AI SRE's incident dashboard — an agent's investigation and a human's approval, read like an aircraft caution-and-warning panel rather than a SaaS admin screen.

colors:
  primary: "#f9a800"
  secondary: "#8c857e"
  tertiary: "#7fe059"
  neutral: "#0e0a07"
  surface: "#181410"
  overlay: "#251f1b"
  border: "#352f2a"
  on-surface: "#ebe7e4"
  error: "#f64258"

typography:
  display:
    fontFamily: IBM Plex Mono
    fontSize: 48px
    fontWeight: 700
    lineHeight: 1.0
    letterSpacing: -0.02em
    fontFeature: "'tnum' 1"
  headline:
    fontFamily: IBM Plex Mono
    fontSize: 23px
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: IBM Plex Mono
    fontSize: 19px
    fontWeight: 700
    lineHeight: 1.25
  body-md:
    fontFamily: IBM Plex Mono
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.55
  data-lg:
    fontFamily: IBM Plex Mono
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.4
    fontFeature: "'tnum' 1"
  data-sm:
    fontFamily: IBM Plex Mono
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.4
    fontFeature: "'tnum' 1"
  caption:
    fontFamily: IBM Plex Mono
    fontSize: 11px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0.01em
  label-caps:
    fontFamily: Departure Mono
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.3
    letterSpacing: 0.15em

omitted:
  - section: rounded
    reason: "Zero-radius is a fixed property of the Retro-Futurist HUD direction, not a scale — brackets and corner markers substitute for corner rounding entirely."

spacing:
  xs: 4px
  sm: 8px
  md: 12px
  lg: 20px
  xl: 32px

components:
  page:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    padding: "{spacing.lg}"
  divider:
    backgroundColor: "{colors.border}"
    height: 1px
  meta-label:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.secondary}"
    typography: "{typography.data-sm}"
  data-readout:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.on-surface}"
    typography: "{typography.display}"
  badge-nominal:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.tertiary}"
    typography: "{typography.label-caps}"
    padding: "{spacing.xs}"
  badge-caution:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    typography: "{typography.label-caps}"
    padding: "{spacing.xs}"
  badge-warning:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.error}"
    typography: "{typography.label-caps}"
    padding: "{spacing.xs}"
  button-approve:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral}"
    typography: "{typography.label-caps}"
    padding: "{spacing.md}"
  button-approve-hover:
    backgroundColor: "#ffc247"
    textColor: "{colors.neutral}"
  stepper-segment-done:
    backgroundColor: "{colors.tertiary}"
    height: 3px
  stepper-segment-current:
    backgroundColor: "{colors.primary}"
    height: 3px
  stepper-segment-failed:
    backgroundColor: "{colors.error}"
    height: 3px
  stepper-segment-future:
    backgroundColor: "{colors.border}"
    height: 3px
  tooltip:
    backgroundColor: "{colors.overlay}"
    textColor: "{colors.on-surface}"
    typography: "{typography.data-sm}"
    padding: "{spacing.sm}"
---

# Annunciator

## Overview

This is not modeled on Grafana or a status-page template. It's modeled on an aircraft caution-and-warning annunciator panel — the row of amber and red lights a pilot reads, and the standard those lights are built to: green means nominal, amber means something needs a decision, red means stop. That standard exists because a pilot under load has no time to parse a paragraph; the color has to carry the verdict before the text does.

The fit isn't just aesthetic. AI SRE's actual design already works this way: an agent investigates and reaches a verdict, but nothing executes until a human looks at the panel and decides. An annunciator light doesn't act on its own either — it tells the pilot, who acts. The visual language and the system's real architecture are the same shape, which is why this direction was picked over something merely "dark and technical."

What this gives up, on purpose: **warmth, and any claim to being unassuming.** This will not read as a friendly internal tool. It reads as an instrument, meant to be scanned under mild time pressure, not browsed at leisure. For a dashboard whose entire job is "tell me fast whether I need to act," that's the right trade.

Dark only, no light variant. An annunciator panel doesn't have a daytime mode — the backlit readout is the whole concept, and it only exists against a dark face.

## Colors

Three signal colors, each with exactly one meaning, and nothing else permitted to use them. Everything else in the interface is neutral.

- **Primary — Sodium Caution (#f9a800):** the color of low-pressure sodium vapor lighting, chosen because it's a real, narrow-band amber that reads as unmistakably "attention" rather than as a UI accent color. Means exactly one thing: *this needs a human decision now.* Marks `pending_approval`, `executing`, and `verifying` states, and is the fill color of the one button in the system, `button-approve`. A caution light and a caution button sharing a color is the point — approving the action is answering the light.
- **Tertiary — Phosphor Nominal (#7fe059):** the yellow-green of P31 oscilloscope and radar-scope phosphor, not a UI green — it's noticeably more yellow than a typical interface green, which is what makes it read as a screen glow rather than a status pill. The only cool-toned color in the system. Means *resolved, verified healthy.* Never used for anything else; its scarcity is what makes "all clear" findable at a glance in a list of otherwise-amber rows.
- **Error — Warning Red (#f64258):** the red of an annunciator warning lamp — the panel's most serious light, reserved for exactly one condition: remediation was attempted and health did not recover. It never marks a merely-open incident; that's amber's job. Red appearing at all is meant to be rare and load-bearing.
- **Neutral (#0e0a07) and Surface (#181410):** the matte, anti-glare black of a cockpit panel housing, not a UI dark-mode grey. Both carry a small warm tint (OKLCH hue 65, chroma 0.010–0.011) rather than being neutral-grey, because a genuinely neutral black reads as a screenshot of "dark mode," not as a physical panel. Neutral is the page itself; Surface is a panel sitting a half-step above it.
- **Overlay (#251f1b):** a third step up the same warm-black ramp, reserved for anything that floats above the panel — currently only tooltips.
- **Border (#352f2a):** the same ramp again, used exclusively for hairline dividers and the stepper's not-yet-reached segments — never as a fill.
- **Secondary (#8c857e):** a warm, desaturated grey for metadata only — timestamps, service names, incident IDs. It is deliberately unglowing, so it never competes with the three signal colors for attention.
- **On-surface (#ebe7e4):** off-white with the same warm cast as the rest of the ramp, used for the root-cause narrative and evidence text — the one place actual reading happens, as opposed to scanning.

All colors were built in OKLCH and converted to hex, verified against WCAG AA before this file was written: every text/background pair in Components clears 4.5:1 with margin (5.0–16.0:1 across the set). None of the three signal colors are unmodified framework defaults — each was checked against and deliberately shifted away from the nearest stock Tailwind equivalent (amber-500, red-500, green-500) so the palette doesn't quietly collapse into one anyway.

## Typography

One face carries almost everything: **IBM Plex Mono**, chosen because its humanist warmth and superfamily pedigree (it pairs natively with Plex Sans and Plex Serif, should this system ever need either) keep it legible as body text at 13px, which a stricter technical mono often isn't. Tabular figures (`tnum`) are enabled everywhere numbers appear, so the confidence readout and timestamps align instead of jittering.

**Departure Mono** — a genuine pixel/bitmap face — is reserved for exactly one job: the uppercase status labels (`label-caps`), tracked at +0.15em. This is the one place the system allows itself to look overtly like a CRT readout rather than a well-set technical UI, and it's kept to short words (OPEN, INVESTIGATING, RESOLVED) specifically because a pixel face stops being legible past a few characters at speed — using it for anything longer than a status word would cost readability for costume.

The scale runs 11 → 48px on a 1.2 ratio (minor third — dense, many levels), hand-broken at the top: the generated scale tops out near 27px, but `display` jumps to 48px because the confidence readout is meant to function like a gauge value, not a heading, and a gauge needs a real jump to read as one. Tracking is optical — −0.02em at display, neutral through body and data, +0.15em on the uppercase labels per the direction's own convention. Line height moves inversely with size: 1.0 at display, 1.2–1.25 at headlines, 1.55 at body (loosened slightly past the usual 1.4–1.5 for mono because reasoning prose set in a technical face needs the extra air to not feel cramped), 1.4 for data and captions.

Two weights only — 400 and 700 — used for role, never for decoration: 700 marks headlines, the approve button's label, and the display readout; everything else is 400.

Both faces are open-licensed (SIL OFL) and self-hosted; no third-party font CDN. Fallback stacks: `"IBM Plex Mono", ui-monospace, "SF Mono", Consolas, monospace` and `"Departure Mono", "IBM Plex Mono", monospace` — if Departure Mono fails to load, it degrades to the body face rather than to a generic system mono, so a fallback still reads as part of the same system.

## Layout

Single column, max-width 760px, centered — this is a panel meant to be read at a consistent width, not a marketing page needing responsive drama. Two views only: a list (every incident, one row each) and a detail (one incident's full readout). No third navigation level.

The 760px panel width is a layout constraint, not a reading measure — the root-cause narrative and evidence text inside it are separately capped at **65 characters** (`max-width: 65ch` on the text block itself, not the panel). At 13px IBM Plex Mono, an uncapped 760px line runs close to 95 characters, past the point where the eye reliably finds the next line.

Spacing runs on a 4px base (`xs` 4px through `xl` 32px) — tighter than a typical product's 8px base, because density is a feature of this register, not a compromise. Row padding in the list view stays small (`sm`/`md`); the detail view's panels get more air (`lg`) specifically because that's where the reasoning is actually read, not scanned — the same density-contrast device Kiln's own example uses for index-vs-record views, applied here to list-vs-detail instead.

Layout is symmetric and centered, not asymmetric — a deliberate departure from what a Swiss or Editorial direction would do. An instrument panel's readouts are aligned to a center console, not flushed to one edge; asymmetry here would fight the "you are looking at a fixed panel" concept the whole direction rests on.

## Elevation & Depth

Flat, with one exception. There are no drop shadows anywhere — depth is conveyed entirely by the three-step warm-black ladder (Neutral → Surface → Overlay) and by 1px `border` rules, never by blur or offset. A panel sits on the page the way a physical instrument face sits in a console: as a distinct material, not as an object floating above one.

The one exception is motion, which this direction treats as part of depth rather than decoration. Three states get motion, and nothing else does:

- **`pending_approval`** pulses — the status label's opacity breathes between 100% and 55% on a slow, deliberate cycle (not a spring, not an ease-bounce — a flat sine-like fade, the way an indicator lamp on old avionics hardware genuinely dims and brightens rather than blinking hard on/off).
- **`executing`/`verifying`** show a small dot animating in the same slow pulse, paired with the word "restarting…" or "verifying…" — motion here confirms something is actively happening, which is the one legitimate reason for motion in this system.
- Everything else is an instant state flip. No entrance animation on the list, no transition when switching from list to detail view, no hover-lift on rows. A row's only hover feedback is a one-step background lightening (Neutral → Surface), instant, no transition duration at all.

Explicitly: **nothing fades in, nothing slides, nothing scales on hover.** If a future screen wants an entrance animation "to feel polished," that instinct should be overridden — polish in this system comes from the panel being still except where stillness would be dishonest about what's happening.

## Shapes

Zero radius, everywhere, without exception — declared via `omitted` rather than a `rounded: none: 0px` token, since there's no scale here to name, just a single fixed fact about the direction. Corners are handled by the badges' and buttons' 1px borders meeting at a hard right angle, not by rounding.

The stepper is the one place shape carries real information: six flush segments in a row, each `{colors.tertiary}` (done), `{colors.primary}` (current), `{colors.border}` (not yet reached), or a single trailing `{colors.error}` segment replacing the rest when an incident fails partway through. The segments touch with no gap larger than 3px, reading as one continuous bar with a state boundary in it, not six separate chips.

## Components

**Badges (`badge-nominal` / `badge-caution` / `badge-warning`).** Never a filled pill — text in the signal color directly on `{colors.surface}`, the way a lamp's own color is the readout rather than a colored sticker behind neutral text. Always paired with the status word itself (OPEN, RESOLVED, FAILED); the color is confirmation, never the sole carrier of meaning, which also keeps this legible for the roughly 8% of viewers with red/green color vision deficiency — green/amber/red is exactly the axis that fails for them, so the text label is not optional here, it's load-bearing.

**Button (`button-approve` / `button-approve-hover`).** The only button in the system, which is deliberate — if a screen ever needs a second button, that's a sign the screen is doing too much. Filled `{colors.primary}` with `{colors.neutral}` text (verified 9.98:1; the reversed pairing — light text on the amber fill — fails at 1.61:1 and must never be used). Hover brightens the fill to `#ffc247`, a literal value one step up the same ramp, not a new token; there is no lift, scale, or shadow change on hover, consistent with the "instant state flip" rule above.

**Data readout (`data-readout`).** The confidence percentage only. Set in `display`, tabular figures on, right where a real gauge's numeric readout would sit — large enough to be read from across a room, which is the actual design requirement for a caution panel.

**Meta label (`meta-label`).** Incident ID, service name, timestamps. Always `{colors.secondary}`, always `data-sm` or `caption`, never a signal color — metadata competing with a status light for attention would defeat the entire palette discipline.

**Divider.** A 1px `{colors.border}` rule, used between list rows and between panel sections. Never a box; this system has no bordered containers except the stepper and the badges/button, which use their border implicitly through the flat color fill meeting the background at a hard edge.

**Tooltip.** `{colors.overlay}` fill, `{colors.on-surface}` text, `data-sm` type — the one surface a full step brighter than Panel, since it needs to read as genuinely floating above everything else, the single context where that's true.

## Do's and Don'ts

- **Do** treat `{colors.primary}` (amber) as meaning "needs a decision," full stop. It marks `pending_approval`, `executing`, `verifying`, and the approve button. Don't reach for it as a generic "highlight" or "brand" color for anything else — its usefulness depends entirely on that single, consistent meaning.
- **Don't** ever set light text on `{colors.primary}`. That pairing measures 1.61:1 and is not a rounding-error failure — it's unreadable. `button-approve`'s text is always `{colors.neutral}`.
- **Do** reserve `{colors.tertiary}` (green) exclusively for `resolved`. If a future screen wants a generic "success" color for something unrelated to incident resolution, that's a sign a fourth color is needed — don't dilute green's scarcity to cover it.
- **Do** reserve `{colors.error}` (red) exclusively for `failed` — a remediation that was attempted and did not verify healthy. Don't use it for form validation, warnings-in-passing, or anything short of that specific, serious condition.
- **Don't** pair color with color alone anywhere a status is shown. Every badge carries its status word; the color confirms, the text states. This is a hard accessibility floor, not a style preference.
- **Don't** add a rounded corner anywhere, including "just this once" on a new component. The flat-edge language is a stated commitment; one rounded card undoes the instrument-panel read for the whole screen it's on.
- **Do** keep motion to exactly the three cases in Elevation & Depth. Don't add a hover-lift, an entrance fade, or a page transition because a screen "feels static" — static is the design, not a gap in it.
- **Don't** introduce a second button style. One button, one job (approve). If a screen seems to need a second action, the screen has too many actions, not too few button variants.
- **Do** use Departure Mono only for short, all-caps status words. Don't set a sentence, a name, or anything longer than roughly ten characters in it — it stops being legible past that length and the whole point is that it stays readable at speed.
