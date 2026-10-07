import type { CSSProperties } from "react";

export function pill(bg: string, fg: string): CSSProperties {
  return {
    display: "inline-flex",
    fontSize: 12.5,
    fontWeight: 700,
    padding: "5px 13px",
    borderRadius: 999,
    background: bg,
    color: fg,
  };
}

export type Verdict =
  | "False"
  | "Misleading"
  | "Unproven"
  | "Accurate"
  | "Opposed"
  | "Supportive"
  | "Neutral";

export const BADGE: Record<Verdict, CSSProperties> = {
  False: pill("#FDECE7", "#C8462A"),
  Misleading: pill("#FFF3DF", "#A86A08"),
  Unproven: pill("#EEF1F4", "#5C6875"),
  Accurate: pill("#E6F7F1", "#0B7A5C"),
  Opposed: pill("#FDECE7", "#C8462A"),
  Supportive: pill("#E6F7F1", "#0B7A5C"),
  Neutral: pill("#EEF1F4", "#5C6875"),
};
