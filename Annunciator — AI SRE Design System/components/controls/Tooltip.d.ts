import type { ReactNode, CSSProperties } from "react";

/** Overlay-fill tooltip — the only surface that reads as floating. */
export interface TooltipProps {
  /** Tooltip text, data-sm, one line. */
  content: ReactNode;
  placement?: "top" | "bottom";
  /** The trigger. */
  children?: ReactNode;
  style?: CSSProperties;
}

export function Tooltip(props: TooltipProps): JSX.Element;
