import Link from "next/link";
import type { CSSProperties } from "react";
import TrendingPostCard, { TRENDING_POSTS } from "@/components/TrendingPostCard";
import { EXAMPLE_QUERIES } from "@/lib/mockData";

const chipStyle: CSSProperties = {
  fontSize: 13.5,
  fontWeight: 600,
  padding: "8px 16px",
  borderRadius: 999,
  background: "#fff",
  border: 0,
  boxShadow: "0 1px 4px rgba(18,24,31,.07)",
};

export default function Homepage() {
  return (
    <main style={{ maxWidth: 1180, margin: "0 auto", padding: "0 40px" }}>
      <section style={{ padding: "76px 0 8px", maxWidth: 760 }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            background: "#fff",
            borderRadius: 999,
            padding: "7px 16px 7px 12px",
            fontSize: 13,
            fontWeight: 600,
            color: "#4A5560",
            boxShadow: "0 2px 10px rgba(18,24,31,.06)",
            marginBottom: 26,
          }}
        >
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#0FA97F", boxShadow: "0 0 0 4px rgba(15,169,127,.18)" }}></span>
          1.4M posts indexed - updated 12 min ago
        </div>
        <h1
          className="vx-text-pretty"
          style={{ fontSize: 58, lineHeight: 1.04, letterSpacing: "-.038em", fontWeight: 800, margin: "0 0 20px" }}
        >
          Check what a vaccine claim is really doing online.
        </h1>
        <p style={{ fontSize: 18, lineHeight: 1.6, color: "#5C6875", fontWeight: 500, maxWidth: 600, margin: "0 0 36px" }}>
          Paste a claim in your own words or drop the link to a post. VaX scores it against the evidence base, then
          shows you how the conversation around it is actually moving.
        </p>
      </section>

      <section style={{ maxWidth: 916 }}>
        <form
          action="/result"
          method="get"
          style={{
            display: "flex",
            gap: 10,
            alignItems: "center",
            padding: "10px 10px 10px 22px",
            borderRadius: 999,
            background: "#fff",
            boxShadow: "0 8px 30px rgba(18,24,31,.09)",
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#9AA5B1" strokeWidth="2.2" strokeLinecap="round" style={{ flex: "none" }}>
            <circle cx="11" cy="11" r="7"></circle>
            <path d="m16.5 16.5 4 4"></path>
          </svg>
          <input
            type="text"
            name="q"
            placeholder='e.g. "vaccines cause autism" - or paste a post URL'
            style={{ flex: 1, border: 0, background: "transparent", minHeight: 46, fontSize: 17, fontWeight: 500, color: "#12181F", padding: 0 }}
          />
          <button
            type="submit"
            className="vx-btn-brand"
            style={{ border: 0, borderRadius: 999, padding: "14px 30px", color: "#fff", fontWeight: 700, fontSize: 15, flex: "none", boxShadow: "0 6px 16px rgba(15,169,127,.34)" }}
          >
            Analyse
          </button>
        </form>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 18, alignItems: "center" }}>
          <span style={{ fontSize: 13, color: "#8A95A1", fontWeight: 600, marginRight: 4 }}>Try</span>
          {EXAMPLE_QUERIES.map(({ label, query }) => (
            <Link key={label} href={`/result?q=${encodeURIComponent(query)}`} className="vx-chip" style={chipStyle}>
              {label}
            </Link>
          ))}
        </div>
      </section>

      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", margin: "80px 0 20px" }}>
        <h2 style={{ fontSize: 22, fontWeight: 800, letterSpacing: "-.02em", margin: 0 }}>Trending posts</h2>
        <Link href="/trends" style={{ fontSize: 14, fontWeight: 700, color: "#0FA97F" }}>
          All trends -&gt;
        </Link>
      </div>
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 18 }}>
        {TRENDING_POSTS.slice(0, 3).map((p) => (
          <TrendingPostCard key={p.postUrl} post={p} />
        ))}
      </section>
    </main>
  );
}
