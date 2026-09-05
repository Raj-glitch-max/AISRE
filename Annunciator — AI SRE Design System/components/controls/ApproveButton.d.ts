import type { ReactNode, CSSProperties } from "react";

/**
 * The system's single button: amber fill, panel-black label, no lift on hover.
 */
export interface ApproveButtonProps {
  /** Label, all caps, short. Default "APPROVE". */
  children?: ReactNode;
  disabled?: boolean;
  onClick?: () => void;
  style?: CSSProperties;
}

export function ApproveButton(props: ApproveButtonProps): JSX.Element;
