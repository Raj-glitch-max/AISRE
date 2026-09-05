import type { CSSProperties } from "react";

export type StepState = "done" | "current" | "failed" | "future";

/**
 * Six-segment progress bar — the one place shape carries information.
 */
export interface StepperProps {
  /** Explicit per-segment states. Omit to derive from current / failed. */
  steps?: StepState[];
  /** Segment count. Default 6. */
  count?: number;
  /** Zero-based index of the segment in progress. */
  current?: number;
  /** Collapse everything from current onward into one red segment. */
  failed?: boolean;
  /** Optional caption labels under the bar; the current one turns amber. */
  labels?: string[];
  style?: CSSProperties;
}

export function Stepper(props: StepperProps): JSX.Element;
