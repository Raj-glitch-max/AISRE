import React from "react";

/* A panel sits on the page the way an instrument face sits in a console:
   a distinct material, never an object floating above one. No shadow, ever. */
export function Panel({ as = "section", label, actions, flush = false, children, style, ...rest }) {
  const Tag = as;
  return (
    <Tag
      {...rest}
      style={{
        background: "var(--surface-panel)",
        color: "var(--text-body)",
        fontFamily: "var(--type-body-md-family)",
        fontSize: "var(--type-body-md-size)",
        lineHeight: "var(--type-body-md-leading)",
        fontFeatureSettings: "var(--figures-tabular)",
        padding: flush ? 0 : "var(--space-lg)",
        borderRadius: 0,
        boxShadow: "none",
        ...style,
      }}
    >
      {(label || actions) && (
        <header
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            gap: "var(--space-md)",
            marginBottom: "var(--space-md)",
            padding: flush ? "var(--space-lg) var(--space-lg) 0" : 0,
          }}
        >
          {label && (
            <span
              style={
                /* Departure Mono stops being legible past ~10 characters, so a
                   long label stays on the body face rather than costing
                   readability for costume. */
                typeof label === "string" && label.length > 11
                  ? {
                      fontFamily: "var(--type-data-sm-family)",
                      fontSize: "var(--type-data-sm-size)",
                      lineHeight: "var(--type-data-sm-leading)",
                      letterSpacing: "0.08em",
                      color: "var(--text-meta)",
                      textTransform: "uppercase",
                    }
                  : {
                      fontFamily: "var(--type-label-caps-family)",
                      fontSize: "var(--type-label-caps-size)",
                      lineHeight: "var(--type-label-caps-leading)",
                      letterSpacing: "var(--type-label-caps-tracking)",
                      color: "var(--text-meta)",
                      textTransform: "uppercase",
                    }
              }
            >
              {label}
            </span>
          )}
          {actions}
        </header>
      )}
      {children}
    </Tag>
  );
}
