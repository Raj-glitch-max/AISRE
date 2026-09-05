import type { CSSProperties } from "react";

export type IncidentStatus =
  | "open"
  | "investigating"
  | "pending_approval"
  | "executing"
  | "verifying"
  | "resolved"
  | "failed";

/**
 * Annunciator lamp: the status word set in the signal color on panel black.
 */
export interface StatusBadgeProps {
  /** Incident status — picks the signal color, the word, and any motion. */
  status?: IncidentStatus;
  /** Override the tone directly. Prefer status. */
  variant?: "nominal" | "caution" | "warning";
  /** Override the word. Must stay under ~10 characters (Departure Mono). */
  label?: string;
  /** Background it sits on, so the badge matches its surface. Default "panel". */
  on?: "panel" | "page";
  style?: CSSProperties;
}

export function StatusBadge(props: StatusBadgeProps): JSX.Element;
