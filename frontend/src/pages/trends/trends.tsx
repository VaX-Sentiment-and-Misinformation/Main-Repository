import SentimentTrendChart, { SentimentByDisease } from "@/components/SentimentTrendChart";
import TrendingPostCard, { TRENDING_POSTS } from "@/components/TrendingPostCard";
import { TIME_WINDOW_LOWER } from "@/lib/mockData";

export default function Trends() {
  return (
    <main className="vx-rise" style={{ maxWidth: 1180, margin: "0 auto", padding: "44px 40px 0" }}>
      <h1 style={{ fontSize: 42, fontWeight: 800, letterSpacing: "-.035em", margin: "0 0 10px" }}>Trends</h1>
      <p style={{ color: "#6B7684", fontSize: 17, fontWeight: 500, margin: "0 0 34px" }}>
        What the vaccine conversation is doing on X right now, over the {TIME_WINDOW_LOWER}.
      </p>

      <section style={{ marginBottom: 34 }}>
        <h2 style={sectionLabel}>Sentiment over time</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <SentimentTrendChart view="monthly" />
          <SentimentByDisease />
        </div>
      </section>

      <section>
        <h2 style={sectionLabel}>Trending posts</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 18 }}>
          {TRENDING_POSTS.map((p) => (
            <TrendingPostCard key={p.postUrl} post={p} />
          ))}
        </div>
      </section>
    </main>
  );
}

const sectionLabel = { fontSize: 15, fontWeight: 800, color: "#8A95A1", margin: "0 0 14px" } as const;
