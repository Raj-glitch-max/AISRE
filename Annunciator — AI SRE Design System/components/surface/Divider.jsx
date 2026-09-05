import React from "react";

/* A 1px rule. Never a box — this system has no bordered containers. */
export function Divider({ inset = 0, style, ...rest }) {
  return (
    <div
      {...rest}
      role="separator"
      style={{
        height: "var(--hairline)",
        background: "var(--rule-hairline)",
        marginLeft: inset,
        marginRight: inset,
        border: 0,
        ...style,
      }}
    />
  );
}
