import React from "react";

const STATUS = {
  open:             { variant: "caution", label: "OPEN" },
  investigating:    { variant: "caution", label: "INVESTIGATING" },
  pending_approval: { variant: "caution", label: "AWAITING", pulse: true },
  executing:        { variant: "caution", label: "EXECUTING", dot: true },
  verifying:        { variant: "caution", label: "VERIFYING", dot: true },
  resolved:         { variant: "nominal", label: "RESOLVED" },
  failed:           { variant: "warning", label: "FAILED" },
};

const INK = {
  nominal: "var(--signal-nominal)",
  caution: "var(--signal-caution)",
  warning: "var(--signal-warning)",
};

/* Never a filled pill — the signal color is the text, the way a lamp's own
   color is the readout. The status word is load-bearing, not decorative. */
export function StatusBadge({ status, variant, label, on = "panel", style, ...rest }) {
  const spec = (status && STATUS[status]) || {};
  const tone = variant || spec.variant || "caution";
  const word = label || spec.label || "UNKNOWN";
  return (
    <span
      {...rest}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "var(--space-xs)",
        background: on === "page" ? "var(--surface-page)" : "var(--surface-panel)",
        color: INK[tone],
        fontFamily: "var(--type-label-caps-family)",
        fontSize: "var(--type-label-caps-size)",
        lineHeight: "var(--type-label-caps-leading)",
        letterSpacing: "var(--type-label-caps-tracking)",
        padding: "var(--space-xs)",
        borderRadius: 0,
        animation: spec.pulse
          ? "annunciator-pulse var(--pulse-duration) var(--pulse-easing) infinite"
          : "none",
        ...style,
      }}
    >
      {spec.dot && (
        <span
          aria-hidden="true"
          style={{
            width: 6,
            height: 6,
            background: INK[tone],
            animation: "annunciator-pulse var(--pulse-duration) var(--pulse-easing) infinite",
          }}
        />
      )}
      {word}
    </span>
  );
}
