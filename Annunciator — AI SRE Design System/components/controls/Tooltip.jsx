import React from "react";

/* The one surface a full step brighter than Panel — the only genuinely
   floating context in the system. */
export function Tooltip({ content, placement = "top", children, style, ...rest }) {
  const [open, setOpen] = React.useState(false);
  const offset =
    placement === "bottom"
      ? { top: "100%", marginTop: "var(--space-xs)" }
      : { bottom: "100%", marginBottom: "var(--space-xs)" };
  return (
    <span
      {...rest}
      style={{ position: "relative", display: "inline-flex", ...style }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && (
        <span
          role="tooltip"
          style={{
            position: "absolute",
            left: 0,
            ...offset,
            zIndex: 20,
            whiteSpace: "nowrap",
            background: "var(--surface-float)",
            color: "var(--text-body)",
            fontFamily: "var(--type-data-sm-family)",
            fontSize: "var(--type-data-sm-size)",
            lineHeight: "var(--type-data-sm-leading)",
            fontFeatureSettings: "var(--figures-tabular)",
            padding: "var(--space-sm)",
            borderRadius: 0,
            boxShadow: "none",
          }}
        >
          {content}
        </span>
      )}
    </span>
  );
}
