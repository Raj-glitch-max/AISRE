Large gauge-style numeric readout — reserved for the agent's confidence percentage.

```jsx
<DataReadout label="Confidence" value={94} />
```

Do not use it for counts, durations, or any other metric; those are MetaLabel or data-lg type. Never restyle it to headline size — the 48px jump is what makes it read as a gauge.
