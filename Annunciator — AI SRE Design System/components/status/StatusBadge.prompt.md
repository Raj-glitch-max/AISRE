The status lamp — signal-colored text on the panel, one per incident. Always shows the status word; the color only confirms it.

```jsx
<StatusBadge status="pending_approval" />
<StatusBadge status="resolved" />
```

pending_approval breathes 100% to 55%; executing and verifying add a pulsing dot. Green is only ever resolved; red is only ever failed. Never drop the word and keep the color alone.
