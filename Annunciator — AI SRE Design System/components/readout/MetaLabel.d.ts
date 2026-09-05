import type { ReactNode, CSSProperties, ElementType } from "react";

/** Warm-grey metadata text — IDs, service names, timestamps, and caps micro-labels. */
export interface MetaLabelProps {
  children?: ReactNode;
  /** Body-face scale. Ignored when variant="caps". "sm" = 12px (default), "caption" = 11px. */
  size?: "sm" | "caption";
  /**
   * "meta" (default) = IBM Plex Mono metadata.
   * "caps" = the label-caps role: Departure Mono, +0.15em, uppercased.
   * Only use "caps" for labels of roughly ten characters or fewer.
   */
  variant?: "meta" | "caps";
  /** Uppercase the body face without switching to the pixel face — for over-length labels. */
  uppercase?: boolean;
  as?: ElementType;
  style?: CSSProperties;
}

export function MetaLabel(props: MetaLabelProps): JSX.Element;
