import Link from "next/link";
import type { ReactNode } from "react";
import type { MisinformationResult, SentimentLabel, SentimentResult, XPost } from "@/lib/api";
import { pill } from "@/lib/badges";
import { looksVaccineRelated } from "@/lib/topic";

interface ResultProps {
  query: string;
  result: SentimentResult;
  misinformation: MisinformationResult;
  // Streamed LLM explanation of the misinformation label (see app/result/page.tsx)
  explanation?: ReactNode;
}

export default function Result({ query, result, misinformation, explanation }: ResultProps) {
  // Both endpoints fetch the same post, so take it from whichever succeeded
  const post = (result.ok ? result.analysis.post : null) ?? (misinformation.ok ? misinformation.analysis.post : null);

  if (!result.ok && result.invalidInput) return <InputError query={query} error={result.error} />;

  const subject = post ? "post" : "claim";

  return (
    <main className="vx-rise vx-page" style={{ maxWidth: 1180, margin: "0 auto" }}>
      <Link href="/" style={{ fontSize: 14, fontWeight: 700, color: "#6B7684", marginBottom: 22, padding: 0, display: "inline-block" }}>
        &lt;- New search
      </Link>

      <div style={{ marginBottom: 22 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#8A95A1", marginBottom: 10 }}>Analysed {subject}</div>
        {post ? (
          <PostCard post={post} />
        ) : (
          <h1 className="vx-text-pretty" style={{ fontSize: 38, fontWeight: 800, lineHeight: 1.12, letterSpacing: "-.03em", margin: 0, overflowWrap: "anywhere" }}>
            {query}
          </h1>
        )}
      </div>

      {!looksVaccineRelated(post ? post.text : query) && (
        <div role="note" style={{ ...notice, marginBottom: 20 }}>
          <strong style={{ color: "#12181F" }}>This {subject} doesn&apos;t seem to be about vaccines.</strong> Both models are built for vaccine
          claims, so these results may not mean much.
        </div>
      )}

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(460px, 100%), 1fr))", gap: 20, alignItems: "start" }}>
        <MisinformationCard result={misinformation} explanation={explanation} />

        <SentimentCard result={result} />
      </section>
    </main>
  );
}

const card = { background: "#fff", borderRadius: 24, padding: 28, boxShadow: "0 3px 14px rgba(18,24,31,.06)" } as const;
const cardTitle = { fontSize: 19, fontWeight: 800, letterSpacing: "-.02em", margin: 0 } as const;
const footnote = { fontSize: 13, color: "#9AA5B1", fontWeight: 500, margin: "20px 0 0", lineHeight: 1.5 } as const;
const notice = { background: "#FFF3DF", color: "#6B4A0A", borderRadius: 16, padding: "12px 16px", fontSize: 14, fontWeight: 500, lineHeight: 1.5 } as const;

const SENTIMENT_ROWS: { key: SentimentLabel; color: string; label: string }[] = [
  { key: "positive", color: "#0FA97F", label: "Supportive of vaccination" },
  { key: "neutral", color: "#C3CCD5", label: "Neutral or asking questions" },
  { key: "negative", color: "#F0603F", label: "Opposed to vaccination" },
];

function InputError({ query, error }: { query: string; error: string }) {
  return (
    <main className="vx-rise vx-page" style={{ maxWidth: 1180, margin: "0 auto" }}>
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

const compact = new Intl.NumberFormat("en-AU", { notation: "compact", maximumFractionDigits: 1 });

function countLabel(n: number, singular: string, plural = `${singular}s`) {
  return `${compact.format(n)} ${n === 1 ? singular : plural}`;
}

// X serves photos from pbs.twimg.com; videos and GIFs come back as .mp4 links, which can't be shown as images
function isImage(url: string) {
  return !/\.(mp4|m3u8)(\?|$)/i.test(url);
}

// Fetched links ask for the original upload (?name=orig); a thumbnail only needs X's small size
function thumbnail(url: string) {
  return url.includes("pbs.twimg.com") ? url.replace(/([?&]name=)\w+/, "$1small") : url;
}

function PostCard({ post }: { post: XPost }) {
  const date = post.created_at && new Date(post.created_at).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
  const stats = [
    date,
    post.replies != null && countLabel(post.replies, "reply", "replies"),
    post.reposts != null && countLabel(post.reposts, "repost"),
    post.likes != null && countLabel(post.likes, "like"),
    post.views != null && countLabel(post.views, "view"),
  ].filter((s): s is string => Boolean(s));
  const images = post.media_urls.filter(isImage).slice(0, 4);
  const mediaCount = post.media_count ?? post.media_urls.length;
  const initial = (post.author_name || post.author_handle || "?").trim().charAt(0).toUpperCase();

  return (
    <article style={card}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div
          aria-hidden="true"
          style={{ width: 44, height: 44, borderRadius: "50%", background: "#E6F7F1", color: "#0B7A5C", display: "grid", placeItems: "center", fontWeight: 800, fontSize: 18, flex: "none" }}
        >
          {initial}
        </div>
        <div style={{ minWidth: 0, flex: 1, lineHeight: 1.35 }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: "#12181F", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{post.author_name}</div>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: "#8A95A1", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            @{post.author_handle}
          </div>
        </div>
        <a href={post.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 14, fontWeight: 700, color: "#0FA97F", flex: "none" }}>
          View on X -&gt;
        </a>
      </div>

      {post.reply_to_handle && (
        <div style={{ marginTop: 14, fontSize: 13.5, fontWeight: 600, color: "#8A95A1" }}>
          Replying to <span style={{ color: "#0FA97F" }}>@{post.reply_to_handle}</span>
        </div>
      )}

      <p
        className="vx-text-pretty vx-post-text"
        style={{ fontWeight: 600, lineHeight: 1.45, letterSpacing: "-.01em", color: "#12181F", maxWidth: 820, margin: "12px 0 0", whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
      >
        {post.text}
      </p>

      {images.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${images.length}, minmax(0, 1fr))`,
            gap: 6,
            maxWidth: images.length === 1 ? 300 : 150 * images.length,
            marginTop: 16,
            borderRadius: 14,
            overflow: "hidden",
          }}
        >
          {images.map((src) => (
            <a key={src} href={post.url} target="_blank" rel="noopener noreferrer" style={{ display: "block", height: images.length === 1 ? 190 : 120, background: "#EDF1F4" }}>
              {/* External X media of unknown size; next/image would need every size and host configured up front */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={thumbnail(src)} alt="Image attached to the post" loading="lazy" style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
            </a>
          ))}
        </div>
      )}

      {stats.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 16px", marginTop: 16, fontSize: 13.5, fontWeight: 600, color: "#9AA5B1" }}>
          {stats.map((s) => (
            <span key={s}>{s}</span>
          ))}
        </div>
      )}

      {post.has_community_note && (
        <div style={{ ...notice, marginTop: 16 }}>
          <strong style={{ color: "#12181F" }}>X has added a Community Note to this post.</strong>{" "}
          <a href={post.url} target="_blank" rel="noopener noreferrer" style={{ color: "#A86A08", fontWeight: 700 }}>
            Read it on X
          </a>{" "}
          for context from other users.
        </div>
      )}

      {(mediaCount > 0 || post.is_quote) && (
        <p style={{ ...footnote, margin: "14px 0 0" }}>
          Only the post&apos;s text was analysed
          {mediaCount > 0 && `, not its ${mediaCount === 1 ? "attachment" : `${mediaCount} attachments`}`}
          {post.is_quote && `${mediaCount > 0 ? " or" : ", not"} the post it quotes`}.
        </p>
      )}
    </article>
  );
}

// Score bands for the meter: the model's probability that the text is misinformation, as 0-100
const RISK_BANDS = [
  { min: 70, label: "HIGH RISK", color: "#F0603F", summary: "The misinformation model flags this as likely vaccine misinformation." },
  { min: 40, label: "MEDIUM RISK", color: "#E8A33D", summary: "The misinformation model is unsure whether this is vaccine misinformation." },
  { min: 0, label: "LOW RISK", color: "#0FA97F", summary: "The misinformation model doesn't flag this as vaccine misinformation." },
];
const RING_CIRCUMFERENCE = 478; // 2 * pi * r for r = 76, matches the vx-ring animation offset

function MisinformationCard({ result, explanation }: { result: MisinformationResult; explanation?: ReactNode }) {
  const title = <h2 style={{ ...cardTitle, marginBottom: 18 }}>Misinformation risk</h2>;

  if (!result.ok) {
    return (
      <div style={card}>
        {title}
        <p style={footnote}>{result.error}</p>
      </div>
    );
  }

  const score = Math.round(result.analysis.scores.misinformation * 100);
  const band = RISK_BANDS.find((b) => score >= b.min)!;
  return (
    <div style={card}>
      {title}
      <div className="vx-meter-top">
        <svg
          role="img"
          aria-label={`Misinformation score ${score} out of 100, ${band.label.toLowerCase()}`}
          width="156"
          height="156"
          viewBox="11 11 174 174" // cropped to the ring's outer edge (r 76 + half the 22 stroke) so it lines up with the title
          style={{ transform: "rotate(-90deg)" }}
        >
          <circle cx="98" cy="98" r="76" fill="none" stroke="#EDF1F4" strokeWidth="22"></circle>
          {score > 0 && (
            <circle
              className="vx-ring"
              cx="98"
              cy="98"
              r="76"
              fill="none"
              stroke={band.color}
              strokeWidth="22"
              strokeLinecap="round"
              strokeDasharray={`${(score / 100) * RING_CIRCUMFERENCE} ${RING_CIRCUMFERENCE}`}
            ></circle>
          )}
          <g transform="rotate(90 98 98)" aria-hidden="true">
            {/* Baselines chosen so the two lines together are centred in the ring (the number's cap height sets the top) */}
            <text x="98" y="101.5" textAnchor="middle" fontFamily="Manrope" fontSize="46" fontWeight="800" fill="#12181F">
              {score}
            </text>
            <text x="98" y="127.5" textAnchor="middle" fontFamily="Manrope" fontSize="14" fontWeight="700" fill={band.color}>
              {band.label}
            </text>
          </g>
        </svg>
        <div style={{ minWidth: 0 }}>
          <div className="vx-text-pretty" style={{ fontSize: 17, fontWeight: 700, lineHeight: 1.4, color: "#12181F" }}>
            {band.summary}
          </div>
          <div style={{ marginTop: 8, fontSize: 13.5, fontWeight: 600, color: "#8A95A1" }}>Model score {score} / 100</div>
        </div>
      </div>

      {explanation && (
        <div style={{ marginTop: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
            <h3 style={{ fontSize: 15, fontWeight: 800, margin: 0 }}>Why?</h3>
            <span style={pill("#EEF1F4", "#5C6875")}>AI-generated</span>
          </div>
          <div style={{ background: "#F6F8FA", borderRadius: 16, padding: 16, fontSize: 14.5, lineHeight: 1.6, color: "#3B4650", fontWeight: 500 }}>
            {explanation}
          </div>
        </div>
      )}

      <p style={footnote}>
        Automated estimate from two AI models, not a fact-check. The model can miss misinformation. Check claims against trusted health sources.
      </p>
    </div>
  );
}

function SentimentCard({ result }: { result: SentimentResult }) {
  const title = <h2 style={{ ...cardTitle, marginBottom: 16 }}>Stance on vaccines</h2>;

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
