import type { CSSProperties } from "react";

/** 1px border-colored rule used between list rows and panel sections. */
export interface DividerProps {
  /** Horizontal inset in px or any CSS length. Default 0 (full bleed). */
  inset?: number | string;
  style?: CSSProperties;
}

export function Divider(props: DividerProps): JSX.Element;
