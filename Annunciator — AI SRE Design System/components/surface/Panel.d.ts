import type { ReactNode, CSSProperties, ElementType } from "react";

/**
 * Flat warm-black panel a half-step above the page. No radius, no shadow.
 */
export interface PanelProps {
  /** Element to render. Default "section". */
  as?: ElementType;
  /**
   * Optional uppercase label in metadata grey. Labels of 11 characters or
   * fewer render in Departure Mono at +0.15em; longer ones fall back to the
   * body face, since the pixel face is illegible past roughly ten characters.
   */
  label?: ReactNode;
  /** Right-aligned slot on the label row — a badge or readout, never a second button. */
  actions?: ReactNode;
  /** Drop the 20px padding so rows can run edge to edge (list views). */
  flush?: boolean;
  children?: ReactNode;
  style?: CSSProperties;
}

export function Panel(props: PanelProps): JSX.Element;
