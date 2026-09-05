import React from "react";

/* The only button in the system. If a screen needs a second one,
   the screen is doing too much. Light text on amber fails 1.61:1 — never. */
export function ApproveButton({ children = "APPROVE", disabled = false, onClick, style, ...rest }) {
  const [hover, setHover] = React.useState(false);
  return (
    <button
      {...rest}
      type="button"
      disabled={disabled}
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        appearance: "none",
        border: 0,
        borderRadius: 0,
        cursor: disabled ? "default" : "pointer",
        background: disabled ? "var(--surface-float)" : hover ? "var(--action-fill-hover)" : "var(--action-fill)",
        color: disabled ? "var(--text-meta)" : "var(--action-ink)",
        fontFamily: "var(--type-label-caps-family)",
        fontSize: "var(--type-label-caps-size)",
        fontWeight: 700,
        lineHeight: "var(--type-label-caps-leading)",
        letterSpacing: "var(--type-label-caps-tracking)",
        padding: "var(--space-md)",
        transition: "none",
        transform: "none",
        boxShadow: "none",
        ...style,
      }}
    >
      {children}
    </button>
  );
}
