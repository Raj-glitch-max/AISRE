Metadata text in warm grey, and the system's only micro-label — IDs, service names, timestamps, and the uppercase headings above content blocks.

```jsx
<MetaLabel>INC-4471 · checkout-api · 14:02:18 UTC</MetaLabel>
<MetaLabel variant="caps">Evidence</MetaLabel>
```

`variant="caps"` is the label-caps role — Departure Mono, +0.15em, uppercased — and it is capped at roughly ten characters, because the pixel face stops being legible past that. For a longer micro-label use `uppercase` instead, which uppercases the body face and keeps it readable. Never override the color to a signal color.
