import Link from "next/link";
import type { SentimentAnalysis, SentimentLabel } from "@/lib/api";

interface ResultProps {
  query: string;
  sentiment: SentimentAnalysis | null;
}

export default function Result({ query, sentiment }: ResultProps) {
  return (
    <main className="vx-rise" style={{ maxWidth: 1180, margin: "0 auto", padding: "36px 40px 0" }}>
      <Link href="/" style={{ fontSize: 14, fontWeight: 700, color: "#6B7684", marginBottom: 22, padding: 0, display: "inline-block" }}>
        &lt;- New search
      </Link>

      <div style={{ marginBottom: 22 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#8A95A1", marginBottom: 10 }}>Analysed claim</div>
        <h1 className="vx-text-pretty" style={{ fontSize: 38, fontWeight: 800, lineHeight: 1.12, letterSpacing: "-.03em", margin: 0 }}>
          {query}
        </h1>
      </div>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(460px, 1fr))", gap: 20 }}>
        <div style={card}>
          <h2 style={{ ...cardTitle, marginBottom: 8 }}>Misinformation meter</h2>
          <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", columnGap: 28, rowGap: 10, alignItems: "center", marginTop: 14 }}>
            <svg width="196" height="196" viewBox="0 0 196 196" style={{ transform: "rotate(-90deg)" }}>
              <circle cx="98" cy="98" r="76" fill="none" stroke="#EDF1F4" strokeWidth="22"></circle>
              <circle
                className="vx-ring"
                cx="98"
                cy="98"
                r="76"
                fill="none"
                stroke="#F0603F"
                strokeWidth="22"
                strokeLinecap="round"
                strokeDasharray="353 478"
              ></circle>
              <g transform="rotate(90 98 98)">
                <text x="98" y="94" textAnchor="middle" fontFamily="Manrope" fontSize="46" fontWeight="800" fill="#12181F">
                  74
                </text>
                <text x="98" y="120" textAnchor="middle" fontFamily="Manrope" fontSize="14" fontWeight="700" fill="#F0603F">
                  HIGH RISK
                </text>
              </g>
            </svg>
            <div style={{ gridRow: 1, gridColumn: 2, minWidth: 0, display: "flex", flexDirection: "column", gap: 14, fontSize: 14.5, lineHeight: 1.5, color: "#6B7684", fontWeight: 500 }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#12181F" }}>
                The claim contradicts the evidence base and is being amplified faster than corrections to it.
              </div>
              <div>
                <span style={{ color: "#12181F", fontWeight: 700 }}>Contradicted by consensus.</span> Nine large cohort studies find no
                association; the retracted 1998 paper remains the source of most reposts.
              </div>
              <div>
                <span style={{ color: "#12181F", fontWeight: 700 }}>Spread outpaces correction 3.4:1</span> - false posts travel further
                than the fact-checks replying to them.
              </div>
            </div>
            <span style={{ gridColumn: 1, justifySelf: "center", fontSize: 13, fontWeight: 600, color: "#9AA5B1" }}>Confidence 0.91</span>
          </div>
        </div>

        <SentimentCard analysis={sentiment} />
      </section>
    </main>
  );
}

const card = { background: "#fff", borderRadius: 24, padding: 28, boxShadow: "0 3px 14px rgba(18,24,31,.06)" } as const;
const cardTitle = { fontSize: 19, fontWeight: 800, letterSpacing: "-.02em", margin: 0 } as const;
const footnote = { fontSize: 13, color: "#9AA5B1", fontWeight: 500, margin: "20px 0 0", lineHeight: 1.5 } as const;

const SENTIMENT_ROWS: { key: SentimentLabel; color: string; label: string }[] = [
  { key: "positive", color: "#0FA97F", label: "Supportive of vaccination" },
  { key: "neutral", color: "#C3CCD5", label: "Neutral or asking questions" },
  { key: "negative", color: "#F0603F", label: "Opposed to vaccination" },
];

function SentimentCard({ analysis }: { analysis: SentimentAnalysis | null }) {
  const title = <h2 style={{ ...cardTitle, marginBottom: 16 }}>In support of vaccines?</h2>;

  if (!analysis) {
    return (
      <div style={card}>
        {title}
        <p style={footnote}>Couldn&apos;t reach the sentiment model. Check that the backend and model service are running and try again.</p>
      </div>
    );
  }

  const { label, scores } = analysis;
  const top = SENTIMENT_ROWS.find((r) => r.key === label)!;
  return (
    <div style={card}>
      {title}
      <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 14.5, fontWeight: 600, color: "#3B4650", marginBottom: 20 }}>
        <span>This claim reads as</span>
        <span style={{ display: "flex", alignItems: "center", gap: 7, padding: "4px 12px", borderRadius: 999, background: "#F3F5F7", fontWeight: 800, color: "#12181F" }}>
          <span style={{ width: 10, height: 10, borderRadius: "50%", background: top.color }}></span>
          {top.label}
        </span>
      </div>
      <div style={{ display: "flex", gap: 4, height: 40, marginBottom: 20 }}>
        {SENTIMENT_ROWS.filter((r) => scores[r.key] >= 0.01).map((r) => (
          <div key={r.key} style={{ flex: scores[r.key], background: r.color, borderRadius: 999 }}></div>
        ))}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {SENTIMENT_ROWS.map((r) => (
          <SentimentRow key={r.key} color={r.color} label={r.label} pct={`${Math.round(scores[r.key] * 100)}%`} />
        ))}
      </div>
      <p style={footnote}>The sentiment model&apos;s confidence that the claim takes each stance on vaccination.</p>
    </div>
  );
}

function SentimentRow({ color, label, pct }: { color: string; label: string; pct: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 14.5, fontWeight: 600 }}>
      <span style={{ width: 12, height: 12, borderRadius: "50%", background: color, flex: "none" }}></span>
      <span style={{ flex: 1, color: "#3B4650" }}>{label}</span>
      <span style={{ fontWeight: 800, fontSize: 16 }}>{pct}</span>
    </div>
  );
}
