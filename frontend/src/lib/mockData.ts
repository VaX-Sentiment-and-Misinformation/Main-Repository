import type { Verdict } from "@/lib/badges";

export const DEFAULT_QUERY = "Vaccines cause autism";
export const TIME_WINDOW = "Last 30 days";
export const TIME_WINDOW_LOWER = TIME_WINDOW.replace("Last ", "last ");

// label is what the chip shows, query is what gets analysed
export const EXAMPLE_QUERIES = [
  { label: "Vaccines cause autism", query: "Vaccines cause autism" },
  { label: "The schedule is too many shots at once", query: "The schedule is too many shots at once" },
  { label: "x.com/CPRNews/status/1344...", query: "https://x.com/CPRNews/status/1344794822691983360" },
];

export function trendScoreColor(pct: number) {
  return pct > 70 ? "#F0603F" : pct > 45 ? "#C88A08" : "#0FA97F";
}

export function trendBarColor(pct: number) {
  return pct > 70 ? "#F0603F" : pct > 45 ? "#F5A623" : "#0FA97F";
}

export interface Claim {
  text: string;
  posts: string;
  verdict: Verdict;
  reach: string;
}

export const TOP_CLAIMS: Claim[] = [
  { text: "The 1998 Lancet study proved a link to autism", posts: "6,120", verdict: "False", reach: "14.2M" },
  { text: "Autism diagnoses rose alongside the vaccine schedule", posts: "3,845", verdict: "Misleading", reach: "8.9M" },
  { text: "Aluminium adjuvants cause neurological damage", posts: "2,610", verdict: "Unproven", reach: "5.1M" },
  { text: "Large cohort studies found no association", posts: "2,204", verdict: "Accurate", reach: "3.4M" },
];
