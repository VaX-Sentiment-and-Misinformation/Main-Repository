import Link from "next/link";
import { BADGE } from "@/lib/badges";
import { DEFAULT_QUERY, TIME_WINDOW, TOP_CLAIMS } from "@/lib/mockData";

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

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 24, alignItems: "start", marginBottom: 22 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#8A95A1", marginBottom: 10 }}>Analysed claim</div>
          <h1 className="vx-text-pretty" style={{ fontSize: 38, fontWeight: 800, lineHeight: 1.12, letterSpacing: "-.03em", margin: "0 0 18px" }}>
            {displayQuery}
          </h1>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <span style={pillTag}>18,412 posts</span>
            <span style={pillTag}>X only</span>
            <span style={pillTag}>{TIME_WINDOW}</span>
            <span style={{ ...pillTag, background: "#E6F7F1", color: "#0B7A5C" }}>Reviewed against 9 sources</span>
          </div>
        </div>
        <div style={{ borderRadius: 24, padding: 24, background: "linear-gradient(150deg,#FF8A6B,#F0603F)", boxShadow: "0 10px 30px rgba(240,96,63,.28)" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
            <span style={{ fontSize: 52, fontWeight: 800, letterSpacing: "-.04em", color: "#fff", lineHeight: 1 }}>74</span>
            <span style={{ fontSize: 15, fontWeight: 600, color: "rgba(255,255,255,.82)" }}>/ 100 misinformation score</span>
          </div>
          <div style={{ fontSize: 16, lineHeight: 1.45, fontWeight: 600, marginTop: 10, color: "#fff" }}>
            High risk. The claim contradicts the evidence base and is being amplified faster than corrections to it.
          </div>
        </div>
      </div>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(460px, 1fr))", gap: 20 }}>
        <div style={card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
            <h2 style={cardTitle}>Misinformation meter</h2>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#9AA5B1" }}>Confidence 0.91</span>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 28, alignItems: "center", marginTop: 14 }}>
            <svg width="196" height="196" viewBox="0 0 196 196" style={{ flex: "none", transform: "rotate(-90deg)" }}>
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
            <div style={{ flex: 1, minWidth: 230, display: "flex", flexDirection: "column", gap: 14, fontSize: 14.5, lineHeight: 1.5, color: "#6B7684", fontWeight: 500 }}>
              <div>
                <span style={{ color: "#12181F", fontWeight: 700 }}>Contradicted by consensus.</span> Nine large cohort studies find no
                association; the retracted 1998 paper remains the source of most reposts.
              </div>
              <div>
                <span style={{ color: "#12181F", fontWeight: 700 }}>Spread outpaces correction 3.4:1</span> - false posts travel further
                than the fact-checks replying to them.
              </div>
            </div>
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

      <section style={{ ...card, marginTop: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: 12, marginBottom: 22 }}>
          <h2 style={cardTitle}>Sentiment over time</h2>
          <div style={{ display: "flex", gap: 18, fontSize: 13, fontWeight: 600, color: "#6B7684" }}>
            <LegendDot color="#0FA97F" label="Supportive" />
            <LegendDot color="#C3CCD5" label="Neutral" />
            <LegendDot color="#F0603F" label="Opposed" />
          </div>
        </div>
        <svg viewBox="0 0 640 210" width="100%" height="220" preserveAspectRatio="xMidYMid meet" style={{ overflow: "visible" }}>
          <defs>
            <linearGradient id="vxfill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#F0603F" stopOpacity=".22"></stop>
              <stop offset="100%" stopColor="#F0603F" stopOpacity="0"></stop>
            </linearGradient>
          </defs>
          <g stroke="#EDF1F4" strokeWidth="1.5">
            <line x1="0" y1="0" x2="640" y2="0"></line>
            <line x1="0" y1="60" x2="640" y2="60"></line>
            <line x1="0" y1="120" x2="640" y2="120"></line>
            <line x1="0" y1="180" x2="640" y2="180"></line>
          </g>
          <path d="M0,66 55,60 109,63 164,51 218,42 273,48 327,36 382,24 436,33 491,45 545,39 600,45 L600,180 L0,180 Z" fill="url(#vxfill)"></path>
          <polyline
            fill="none"
            stroke="#F0603F"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points="0,66 55,60 109,63 164,51 218,42 273,48 327,36 382,24 436,33 491,45 545,39 600,45"
          ></polyline>
          <polyline
            fill="none"
            stroke="#0FA97F"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points="0,78 55,81 109,75 164,84 218,90 273,87 327,93 382,99 436,93 491,87 545,90 600,87"
          ></polyline>
          <polyline
            fill="none"
            stroke="#C3CCD5"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            points="0,96 55,99 109,102 164,105 218,108 273,105 327,111 382,117 436,114 491,108 545,111 600,108"
          ></polyline>
          <line x1="382" y1="14" x2="382" y2="180" stroke="#C3CCD5" strokeWidth="1.5" strokeDasharray="4 5"></line>
          <circle cx="382" cy="24" r="6" fill="#fff" stroke="#F0603F" strokeWidth="3.5"></circle>
          <text x="392" y="12" fontFamily="Manrope" fontSize="13" fontWeight="700" fill="#6B7684">
            Podcast clip, 2.1M views
          </text>
          <text x="0" y="202" fontFamily="Manrope" fontSize="12.5" fontWeight="600" fill="#9AA5B1">
            Jul 12
          </text>
          <text x="600" y="202" fontFamily="Manrope" fontSize="12.5" fontWeight="600" fill="#9AA5B1" textAnchor="end">
            Aug 10
          </text>
        </svg>
      </section>

      <section style={{ ...card, marginTop: 20 }}>
        <h2 style={{ ...cardTitle, marginBottom: 18 }}>Top claims detected</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {TOP_CLAIMS.map((cl) => (
            <div
              key={cl.text}
              style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap", padding: "16px 18px", borderRadius: 18, background: "#F7F9FA" }}
            >
              <span style={{ flex: 1, minWidth: 220, fontSize: 15, fontWeight: 600, color: "#12181F" }}>{cl.text}</span>
              <span style={BADGE[cl.verdict]}>{cl.verdict}</span>
              <span style={{ width: 92, textAlign: "right", fontSize: 13.5, fontWeight: 600, color: "#8A95A1" }}>{cl.posts} posts</span>
              <span style={{ width: 70, textAlign: "right", fontSize: 15, fontWeight: 800, color: "#3B4650" }}>{cl.reach}</span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

const card = { background: "#fff", borderRadius: 24, padding: 28, boxShadow: "0 3px 14px rgba(18,24,31,.06)" } as const;
const cardTitle = { fontSize: 19, fontWeight: 800, letterSpacing: "-.02em", margin: 0 } as const;
const pillTag = {
  display: "inline-flex",
  fontSize: 13,
  fontWeight: 600,
  padding: "7px 14px",
  borderRadius: 999,
  background: "#fff",
  color: "#5C6875",
  boxShadow: "0 1px 4px rgba(18,24,31,.06)",
} as const;

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

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 7 }}>
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: color }}></span>
      {label}
    </span>
  );
}
