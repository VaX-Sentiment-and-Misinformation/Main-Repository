import Link from "next/link";
import trending from "@/data/trendingPosts.json";
import { BADGE, type Verdict } from "@/lib/badges";
import { trendBarColor, trendScoreColor } from "@/lib/mockData";

// Built by backend/scripts/build_trending_posts.py from the latest Apify scrape, most engaged first
export const TRENDING_POSTS = trending.posts;

export type TrendingPost = (typeof TRENDING_POSTS)[number];

// Sentiment model label -> the badge the rest of the site shows for it
const SENTIMENT_BADGE: Record<string, Verdict> = { negative: "Opposed", neutral: "Neutral", positive: "Supportive" };

export default function TrendingPostCard({ post: p }: { post: TrendingPost }) {
  const sentiment = SENTIMENT_BADGE[p.sentiment];
  return (
    <article
      className="vx-trend-card"
      style={{ position: "relative", background: "#fff", borderRadius: 24, padding: 24, display: "flex", flexDirection: "column", gap: 12, minHeight: 232 }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={BADGE[sentiment]}>{sentiment}</span>
        <span style={{ fontSize: 12.5, color: "#9AA5B1", fontWeight: 600 }}>{p.likes}</span>
      </div>
      <div style={{ minWidth: 0 }}>
        <h3 style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-.02em", margin: 0, color: "#12181F", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {p.author}
        </h3>
        <span style={{ fontSize: 13, fontWeight: 600, color: "#9AA5B1" }}>@{p.handle}</span>
      </div>
      <p style={{ margin: 0, flex: 1, fontSize: 14, lineHeight: 1.55, color: "#6B7684", fontWeight: 500 }}>&ldquo;{p.body}&rdquo;</p>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 2 }} title={`Misinformation model: ${p.score} likely misinformation`}>
        <span style={{ fontSize: 12.5, fontWeight: 600, color: "#9AA5B1" }}>Misinfo</span>
        <div style={{ flex: 1, height: 8, borderRadius: 999, background: "#EDF1F4", overflow: "hidden" }}>
          <div style={{ width: `${p.pct}%`, height: "100%", borderRadius: 999, background: trendBarColor(p.pct) }}></div>
        </div>
        <span style={{ fontSize: 15, fontWeight: 800, color: trendScoreColor(p.pct) }}>{p.score}</span>
      </div>
      <span style={{ fontSize: 13.5, fontWeight: 700, color: "#0FA97F" }}>Analyse this post -&gt;</span>
      <Link
        href={`/result?q=${encodeURIComponent(p.postUrl)}`}
        aria-label={`Analyse @${p.handle}'s post`}
        style={{ position: "absolute", inset: 0, borderRadius: 24 }}
      ></Link>
    </article>
  );
}
