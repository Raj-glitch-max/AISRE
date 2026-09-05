Flat panel surface — use it for any block of content sitting on the page, and for the container of a list of incident rows.

```jsx
<Panel label="Root cause" actions={<StatusBadge status="pending_approval" />}>
  <p style={{ maxWidth: "var(--measure)" }}>Connection pool exhaustion on checkout-api…</p>
</Panel>
```

Variants: `flush` removes padding for edge-to-edge rows; `label` sets the caps header; `actions` holds one badge or readout. Never add a shadow, border-radius, or a second button.
