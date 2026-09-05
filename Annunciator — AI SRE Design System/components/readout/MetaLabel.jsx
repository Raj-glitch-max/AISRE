import React from "react";

/* Incident IDs, service names, timestamps. Never a signal color.
   variant="caps" is the label-caps role: Departure Mono, +0.15em, uppercase.
   Keep caps labels to roughly ten characters — the pixel face stops being
   legible past that, so anything longer must stay on the body face. */
export function MetaLabel({ children, size = "sm", variant = "meta", uppercase = false, as = "span", style, ...rest }) {
  const Tag = as;
  const caps = variant === "caps";
  const s = caps ? "label-caps" : size === "caption" ? "caption" : "data-sm";
  return (
    <Tag
      {...rest}
      style={{
        fontFamily: "var(--type-" + s + "-family)",
        fontSize: "var(--type-" + s + "-size)",
        fontWeight: "var(--type-" + s + "-weight)",
        lineHeight: "var(--type-" + s + "-leading)",
        letterSpacing: "var(--type-" + s + "-tracking)",
        fontFeatureSettings: caps ? "normal" : "var(--figures-tabular)",
        color: "var(--text-meta)",
        textTransform: caps || uppercase ? "uppercase" : "none",
        ...style,
      }}
    >
      {children}
    </Tag>
  );
}
