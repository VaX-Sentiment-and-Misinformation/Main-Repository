import Link from "next/link";
import { BADGE } from "@/lib/badges";
import { POSTS, TIME_WINDOW_LOWER, TOPICS, topicDeltaColor } from "@/lib/mockData";

export default function Trends() {
  return (
    <main className="vx-rise" style={{ maxWidth: 1180, margin: "0 auto", padding: "44px 40px 0" }}>
      <h1 style={{ fontSize: 42, fontWeight: 800, letterSpacing: "-.035em", margin: "0 0 10px" }}>Trends</h1>
      <p style={{ color: "#6B7684", fontSize: 17, fontWeight: 500, margin: "0 0 34px" }}>
        What the vaccine conversation is doing on X right now, over the {TIME_WINDOW_LOWER}.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: 20, alignItems: "start" }}>
        <section>
          <h2 style={sectionLabel}>Popular topics</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {TOPICS.map((t) => (
              <article
                key={t.name}
                className="vx-topic-card"
                style={{ position: "relative", background: "#fff", borderRadius: 22, padding: "18px 20px", display: "flex", flexDirection: "column", gap: 10 }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <span style={{ fontSize: 13, fontWeight: 800, color: "#C3CCD5", width: 22 }}>{t.rank}</span>
                  <span style={{ flex: 1, fontSize: 17, fontWeight: 700, letterSpacing: "-.015em", color: "#12181F" }}>{t.name}</span>
                  <span style={{ fontSize: 13.5, fontWeight: 800, color: topicDeltaColor(t.delta) }}>{t.delta}</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 14, paddingLeft: 36 }}>
                  <svg width="120" height="26" viewBox="0 0 120 26" style={{ flex: "none" }}>
                    <polyline fill="none" stroke="#0FA97F" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" points={t.spark}></polyline>
                  </svg>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#9AA5B1", flex: 1 }}>{t.volume}</span>
                  <span style={BADGE[t.verdict]}>{t.verdict}</span>
                </div>
                <Link href={`/result?q=${encodeURIComponent(t.name)}`} aria-label={t.name} style={{ position: "absolute", inset: 0, borderRadius: 22 }}></Link>
              </article>
            ))}
          </div>
        </section>

        <section>
          <h2 style={sectionLabel}>What users are thinking</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {POSTS.map((p) => (
              <article
                key={p.handle + p.time}
                style={{ background: "#fff", borderRadius: 22, padding: "18px 20px", display: "flex", flexDirection: "column", gap: 12, boxShadow: "0 3px 14px rgba(18,24,31,.06)" }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <span style={{ width: 30, height: 30, borderRadius: "50%", background: "linear-gradient(145deg,#DCE4EA,#C3CCD5)", flex: "none" }}></span>
                  <span style={{ fontSize: 14.5, fontWeight: 700 }}>{p.handle}</span>
                  <span style={BADGE[p.sentiment]}>{p.sentiment}</span>
                </div>
                <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.5, fontWeight: 500, color: "#2A3440" }}>{p.text}</p>
                <div style={{ display: "flex", alignItems: "center", gap: 18, fontSize: 13, fontWeight: 600, color: "#9AA5B1" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#F0603F" strokeWidth="2.2" strokeLinejoin="round">
                      <path d="M12 20s-7-4.4-7-9a4 4 0 0 1 7-2.6A4 4 0 0 1 19 11c0 4.6-7 9-7 9Z"></path>
                    </svg>
                    {p.likes}
                  </span>
                  <span>{p.time}</span>
                  <Link href={`/result?q=${encodeURIComponent(p.text)}`} style={{ marginLeft: "auto", fontWeight: 700 }}>
                    Analyse this post -&gt;
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

const sectionLabel = { fontSize: 15, fontWeight: 800, color: "#8A95A1", margin: "0 0 14px" } as const;
