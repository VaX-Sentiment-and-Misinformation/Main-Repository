import Link from "next/link";
import type { SentimentLabel, SentimentResult, XPost } from "@/lib/api";

interface ResultProps {
  query: string;
  result: SentimentResult;
}

export default function Result({ query, result }: ResultProps) {
  const post = result.ok ? result.analysis.post : null;

  if (!result.ok && result.invalidInput) return <InputError query={query} error={result.error} />;

  return (
    <main className="vx-rise" style={{ maxWidth: 1180, margin: "0 auto", padding: "36px 40px 0" }}>
      <Link href="/" style={{ fontSize: 14, fontWeight: 700, color: "#6B7684", marginBottom: 22, padding: 0, display: "inline-block" }}>
        &lt;- New search
      </Link>

      <div style={{ marginBottom: 22 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#8A95A1", marginBottom: 10 }}>{post ? "Analysed post" : "Analysed claim"}</div>
        {post ? (
          <PostCard post={post} />
        ) : (
          <h1 className="vx-text-pretty" style={{ fontSize: 38, fontWeight: 800, lineHeight: 1.12, letterSpacing: "-.03em", margin: 0, overflowWrap: "anywhere" }}>
            {query}
          </h1>
        )}
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

        <SentimentCard result={result} />
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

function InputError({ query, error }: { query: string; error: string }) {
  return (
    <main className="vx-rise" style={{ maxWidth: 1180, margin: "0 auto", padding: "36px 40px 0" }}>
      <Link href="/" style={{ fontSize: 14, fontWeight: 700, color: "#6B7684", marginBottom: 22, padding: 0, display: "inline-block" }}>
        &lt;- New search
      </Link>

      <div role="alert" style={{ ...card, maxWidth: 760 }}>
        <h1 style={{ ...cardTitle, fontSize: 24, marginBottom: 10 }}>We can&apos;t analyse that</h1>
        <p style={{ fontSize: 15.5, lineHeight: 1.55, color: "#3B4650", fontWeight: 500, margin: "0 0 20px" }}>{error}</p>
        <form action="/result" method="get" style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <input
            type="text"
            name="q"
            defaultValue={query}
            aria-label="Claim or X post link"
            style={{ flex: "1 1 260px", minWidth: 0, minHeight: 46, padding: "0 18px", borderRadius: 999, border: "1.5px solid #F0603F", fontSize: 15, fontWeight: 500, color: "#12181F" }}
          />
          <button
            type="submit"
            className="vx-btn-brand"
            style={{ border: 0, borderRadius: 999, padding: "0 26px", minHeight: 46, color: "#fff", fontWeight: 700, fontSize: 15 }}
          >
            Try again
          </button>
        </form>
      </div>
    </main>
  );
}

function PostCard({ post }: { post: XPost }) {
  const stats = [
    post.created_at && new Date(post.created_at).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" }),
    post.likes != null && `${post.likes.toLocaleString("en-AU")} likes`,
    post.reposts != null && `${post.reposts.toLocaleString("en-AU")} reposts`,
  ].filter(Boolean);

  return (
    <article style={{ ...card, maxWidth: 760 }}>
      <div style={{ fontSize: 15, fontWeight: 800, color: "#12181F" }}>
        {post.author_name} <span style={{ fontWeight: 600, color: "#8A95A1" }}>@{post.author_handle}</span>
      </div>
      <p className="vx-text-pretty" style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.35, letterSpacing: "-.02em", margin: "10px 0 14px", whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
        {post.text}
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 14, fontSize: 13.5, fontWeight: 600, color: "#9AA5B1" }}>
        {stats.map((s) => (
          <span key={s as string}>{s}</span>
        ))}
        <a href={post.url} target="_blank" rel="noopener noreferrer" style={{ marginLeft: "auto", fontWeight: 700, color: "#0FA97F" }}>
          View on X -&gt;
        </a>
      </div>
    </article>
  );
}

function SentimentCard({ result }: { result: SentimentResult }) {
  const title = <h2 style={{ ...cardTitle, marginBottom: 16 }}>In support of vaccines?</h2>;

  if (!result.ok) {
    return (
      <div style={card}>
        {title}
        <p style={footnote}>{result.error}</p>
      </div>
    );
  }

  const { label, scores, post } = result.analysis;
  const top = SENTIMENT_ROWS.find((r) => r.key === label)!;
  return (
    <div style={card}>
      {title}
      <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 14.5, fontWeight: 600, color: "#3B4650", marginBottom: 20 }}>
        <span>This {post ? "post" : "claim"} reads as</span>
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
      <p style={footnote}>The sentiment model&apos;s confidence that the {post ? "post" : "claim"} takes each stance on vaccination.</p>
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
