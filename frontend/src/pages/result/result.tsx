import Link from "next/link";
import { DEFAULT_QUERY } from "@/lib/mockData";

interface ResultProps {
  query?: string;
}

export default function Result({ query }: ResultProps) {
  const displayQuery = query?.trim() || DEFAULT_QUERY;

  return (
    <main className="vx-rise" style={{ maxWidth: 1180, margin: "0 auto", padding: "36px 40px 0" }}>
      <Link href="/" style={{ fontSize: 14, fontWeight: 700, color: "#6B7684", marginBottom: 22, padding: 0, display: "inline-block" }}>
        &lt;- New search
      </Link>

      <div style={{ marginBottom: 22 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#8A95A1", marginBottom: 10 }}>Analysed claim</div>
        <h1 className="vx-text-pretty" style={{ fontSize: 38, fontWeight: 800, lineHeight: 1.12, letterSpacing: "-.03em", margin: 0 }}>
          {displayQuery}
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

        <div style={card}>
          <h2 style={{ ...cardTitle, marginBottom: 20 }}>In support of vaccines?</h2>
          <div style={{ display: "flex", gap: 4, height: 40, marginBottom: 20 }}>
            <div style={{ width: "31%", background: "#0FA97F", borderRadius: 999 }}></div>
            <div style={{ width: "24%", background: "#C3CCD5", borderRadius: 999 }}></div>
            <div style={{ width: "45%", background: "#F0603F", borderRadius: 999 }}></div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <SentimentRow color="#0FA97F" label="Supportive of vaccination" pct="31%" count="5,708 posts" />
            <SentimentRow color="#C3CCD5" label="Neutral or asking questions" pct="24%" count="4,419 posts" />
            <SentimentRow color="#F0603F" label="Opposed to vaccination" pct="45%" count="8,285 posts" />
          </div>
          <p style={{ fontSize: 13, color: "#9AA5B1", fontWeight: 500, margin: "20px 0 0", lineHeight: 1.5 }}>
            Sentiment is measured toward vaccination itself, not toward the claim. Posts quoting the claim to debunk it count as
            supportive.
          </p>
        </div>
      </section>
    </main>
  );
}

const card = { background: "#fff", borderRadius: 24, padding: 28, boxShadow: "0 3px 14px rgba(18,24,31,.06)" } as const;
const cardTitle = { fontSize: 19, fontWeight: 800, letterSpacing: "-.02em", margin: 0 } as const;

function SentimentRow({ color, label, pct, count }: { color: string; label: string; pct: string; count: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 14.5, fontWeight: 600 }}>
      <span style={{ width: 12, height: 12, borderRadius: "50%", background: color, flex: "none" }}></span>
      <span style={{ flex: 1, color: "#3B4650" }}>{label}</span>
      <span style={{ fontWeight: 800, fontSize: 16 }}>{pct}</span>
      <span style={{ width: 76, textAlign: "right", color: "#9AA5B1", fontSize: 13 }}>{count}</span>
    </div>
  );
}
