import React from "react";

/* The confidence percentage. Set like a gauge value, not a heading. */
export function DataReadout({ value, unit = "%", label, align = "left", style, ...rest }) {
  return (
    <div {...rest} style={{ textAlign: align, ...style }}>
      {label && (
        <div
          style={{
            fontFamily: "var(--type-label-caps-family)",
            fontSize: "var(--type-label-caps-size)",
            lineHeight: "var(--type-label-caps-leading)",
            letterSpacing: "var(--type-label-caps-tracking)",
            color: "var(--text-meta)",
            textTransform: "uppercase",
            marginBottom: "var(--space-sm)",
          }}
        >
          {label}
        </div>
      )}
      <div
        style={{
          fontFamily: "var(--type-display-family)",
          fontSize: "var(--type-display-size)",
          fontWeight: "var(--type-display-weight)",
          lineHeight: "var(--type-display-leading)",
          letterSpacing: "var(--type-display-tracking)",
          fontFeatureSettings: "var(--figures-tabular)",
          color: "var(--text-body)",
        }}
      >
        {value}
        {unit && (
          <span style={{ fontSize: "0.5em", marginLeft: "0.12em", color: "var(--text-meta)" }}>{unit}</span>
        )}
      </div>
    </div>
  );
}
