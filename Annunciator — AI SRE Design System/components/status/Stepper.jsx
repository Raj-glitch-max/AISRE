import React from "react";

const FILL = {
  done: "var(--signal-nominal)",
  current: "var(--signal-caution)",
  failed: "var(--signal-warning)",
  future: "var(--signal-inert)",
};

/* Six flush segments reading as one bar with a state boundary in it.
   A failed run replaces every remaining segment with a single red one. */
export function Stepper({ steps, count = 6, current = 0, failed = false, labels = [], style, ...rest }) {
  let cells;
  if (steps && steps.length) {
    cells = steps.map((s) => ({ state: s, span: 1 }));
  } else if (failed) {
    cells = [];
    for (let i = 0; i < current; i++) cells.push({ state: "done", span: 1 });
    cells.push({ state: "failed", span: Math.max(1, count - current) });
  } else {
    cells = Array.from({ length: count }, (_, i) => ({
      state: i < current ? "done" : i === current ? "current" : "future",
      span: 1,
    }));
  }
  return (
    <div {...rest} style={style}>
      <div style={{ display: "flex", gap: "var(--space-xs)", alignItems: "stretch" }}>
        {cells.map((c, i) => (
          <div
            key={i}
            style={{ flex: c.span, height: "var(--stepper-height)", background: FILL[c.state] || FILL.future }}
          />
        ))}
      </div>
      {labels.length > 0 && (
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: "var(--space-sm)" }}>
          {labels.map((l, i) => (
            <span
              key={l}
              style={{
                fontFamily: "var(--type-caption-family)",
                fontSize: "var(--type-caption-size)",
                lineHeight: "var(--type-caption-leading)",
                letterSpacing: "var(--type-caption-tracking)",
                color: i === current ? (failed ? "var(--signal-warning)" : "var(--signal-caution)") : "var(--text-meta)",
              }}
            >
              {l}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
