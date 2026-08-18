import type { Kicker, Verdict } from "@/lib/badges";

export const DEFAULT_QUERY = "Vaccines cause autism";
export const TIME_WINDOW = "Last 30 days";
export const TIME_WINDOW_LOWER = TIME_WINDOW.replace("Last ", "last ");

export const EXAMPLE_QUERIES = [
  "Vaccines cause autism",
  "The schedule is too many shots at once",
  "https://x.com/post/1849...",
];

export interface TrendCard {
  kicker: Kicker;
  title: string;
  body: string;
  volume: string;
  score: string;
  pct: number;
}

export const TRENDING_CLAIMS: TrendCard[] = [
  {
    kicker: "Rising",
    title: "mRNA and fertility",
    body: "A recycled 2021 thread claiming vaccines affect fertility is circulating again after a fitness influencer reposted it.",
    volume: "23.1k posts",
    score: "81",
    pct: 81,
  },
  {
    kicker: "Steady",
    title: "Boosters and immunity",
    body: "Genuine debate over booster intervals, with a minority reframing it as evidence the vaccine failed.",
    volume: "11.7k posts",
    score: "34",
    pct: 34,
  },
  {
    kicker: "Cooling",
    title: "Childhood schedule",
    body: "Delay-the-schedule advice is spreading in parenting groups faster than paediatric guidance replying to it.",
    volume: "8.4k posts",
    score: "62",
    pct: 62,
  },
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

export interface Topic {
  rank: string;
  name: string;
  delta: string;
  volume: string;
  verdict: Verdict;
  spark: string;
}

export const TOPICS: Topic[] = [
  { rank: "01", name: "mRNA and fertility", delta: "+240%", volume: "23.1k posts", verdict: "False", spark: "0,22 20,19 40,17 60,13 80,9 100,4 120,2" },
  { rank: "02", name: "Boosters and immunity", delta: "+18%", volume: "11.7k posts", verdict: "Neutral", spark: "0,15 20,16 40,13 60,14 80,12 100,11 120,10" },
  { rank: "03", name: "Childhood schedule", delta: "-9%", volume: "8.4k posts", verdict: "Misleading", spark: "0,7 20,9 40,8 60,11 80,13 100,14 120,16" },
  { rank: "04", name: "Vaccine ingredients", delta: "+31%", volume: "6.9k posts", verdict: "Unproven", spark: "0,19 20,17 40,18 60,14 80,13 100,11 120,9" },
  { rank: "05", name: "Flu shot effectiveness", delta: "+4%", volume: "4.2k posts", verdict: "Accurate", spark: "0,13 20,13 40,12 60,13 80,12 100,12 120,11" },
];

export function topicDeltaColor(delta: string) {
  return delta.startsWith("+") ? "#F0603F" : "#0FA97F";
}

export interface Post {
  handle: string;
  sentiment: "Opposed" | "Supportive" | "Neutral";
  text: string;
  likes: string;
  time: string;
}

export const POSTS: Post[] = [
  { handle: "@marisol_reads", sentiment: "Opposed", text: "My cousin's kid changed after the MMR. Nobody can tell me that's a coincidence.", likes: "12.4k", time: "3h" },
  { handle: "@quietpediatrician", sentiment: "Supportive", text: "I've been in paediatrics 19 years. The schedule is spaced the way it is because those are the months infants are most vulnerable, not for convenience.", likes: "8.9k", time: "6h" },
  { handle: "@dadof3_", sentiment: "Neutral", text: "Genuinely asking - is there a source for the fertility thing or is it just the same screenshot going around?", likes: "3.1k", time: "9h" },
  { handle: "@wellness.kate", sentiment: "Opposed", text: "They never studied them together. That's all I'm saying. Do your own research.", likes: "44.2k", time: "1d" },
  { handle: "@evidencebase", sentiment: "Supportive", text: "The 1998 paper was retracted in 2010 and its author lost his licence. Nine studies since, 1.2M children, no association.", likes: "6.7k", time: "1d" },
];
