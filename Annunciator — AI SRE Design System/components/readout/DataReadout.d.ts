import type { CSSProperties } from "react";

/** Gauge-scale numeric readout (48px, tabular figures). Confidence only. */
export interface DataReadoutProps {
  /** The number itself, e.g. 94. */
  value: number | string;
  /** Trailing unit, rendered half-size in metadata grey. Default "%". */
  unit?: string;
  /** Optional caps label above the number. */
  label?: string;
  align?: "left" | "right" | "center";
  style?: CSSProperties;
}

export function DataReadout(props: DataReadoutProps): JSX.Element;
