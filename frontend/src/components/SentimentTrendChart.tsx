"use client";

import { useState, type CSSProperties } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import trend from "@/data/sentimentTrend.json";

type Sentiment = "negative" | "neutral" | "positive";
type ViewId = "monthly" | "daily" | "quarterly";
type CategoryId = keyof typeof trend.daily.series;

interface Bucket {
  n: number;
  negative?: number;
  neutral?: number;
  positive?: number;
}
interface Period extends Bucket {
  period: string;
}
interface Category extends Bucket {
  id: CategoryId;
  label: string;
}

// Diverging: warm negative, neutral grey midpoint, cool positive. Stacked negative first.
const SERIES: { key: Sentiment; label: string; color: string }[] = [
  { key: "negative", label: "Negative", color: "#F0603F" },
  { key: "neutral", label: "Neutral", color: "#A3AEB9" },
  { key: "positive", label: "Positive", color: "#0FA97F" },
];

const MIN_N = trend.minBucketPosts;

const plotted = (b: Bucket) => b.negative !== undefined;

const dayFmt = new Intl.DateTimeFormat("en-AU", { weekday: "short", day: "numeric", timeZone: "UTC" });
const fullDayFmt = new Intl.DateTimeFormat("en-AU", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
const dayMonthFmt = new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "short", timeZone: "UTC" });
const monthYearFmt = new Intl.DateTimeFormat("en-AU", { month: "short", year: "numeric", timeZone: "UTC" });
const monthFmt = new Intl.DateTimeFormat("en-AU", { month: "short", timeZone: "UTC" });
const fullMonthFmt = new Intl.DateTimeFormat("en-AU", { month: "long", year: "numeric", timeZone: "UTC" });
const toMonth = (month: string) => toDate(`${month}-01`);

// Three years of months is too many labels: tick each quarter, with the year on
// January and on the first month.
const monthTick = (month: string, index: number) => {
  const d = toMonth(month);
  if (d.getUTCMonth() % 3 !== 0 && index !== 0) return "";
  return d.getUTCMonth() === 0 || index === 0 ? monthYearFmt.format(d) : monthFmt.format(d);
};
const toDate = (day: string) => new Date(`${day}T00:00:00Z`);

const QUARTER_MONTHS = ["Jan–Mar", "Apr–Jun", "Jul–Sep", "Oct–Dec"];
const qYear = (period: string) => Number(period.slice(0, 4));
const qNum = (period: string) => Number(period.slice(-1));

interface View {
  // Lines read better than 36 near-identical stacked bars; few periods stay as bars
  chart: "bar" | "line";
  categories: Category[];
  series: Record<CategoryId, Period[]>;
  start: string;
  end: string;
  unit: string;
  tick: (period: string, index: number) => string;
  periodTitle: (period: string) => string;
  firstHeader: string;
  title: (subject: string) => string;
  subtitle: (n: number) => string;
  footnote: string;
}

// monthly follows the scrape each post came from. daily and quarterly follow when
// posts were written: the final week is dense, everything before it a thin sample
// of the most-engaged posts, so the two are charted at different grains.
const VIEWS: Record<ViewId, View> = {
  monthly: {
    ...(trend.monthly as Pick<View, "categories" | "series" | "start" | "end">),
    chart: "line",
    unit: "month",
    tick: monthTick,
    periodTitle: (p) => fullMonthFmt.format(toMonth(p)),
    firstHeader: "Month",
    title: (subject) => `Sentiment towards ${subject}, month by month`,
    subtitle: (n) =>
      `Share of posts per monthly scrape · ${n.toLocaleString()} posts, ${monthYearFmt.format(toMonth(trend.monthly.start))} to ${monthYearFmt.format(toMonth(trend.monthly.end))}`,
    footnote:
      "Each month is the most-engaged vaccine posts X returned when that month was scraped. Popular posts stay popular, so many appear in several months. Sentiment is model-predicted.",
  },
  daily: {
    ...(trend.daily as Pick<View, "categories" | "series" | "start" | "end">),
    chart: "bar",
    unit: "day",
    tick: (p) => dayFmt.format(toDate(p)),
    periodTitle: (p) => fullDayFmt.format(toDate(p)),
    firstHeader: "Day",
    title: (subject) => `Sentiment towards ${subject} this week, day by day`,
    subtitle: (n) =>
      `Share of posts per day · ${n.toLocaleString()} posts, ${dayMonthFmt.format(toDate(trend.daily.start))} to ${dayMonthFmt.format(toDate(trend.daily.end))} ${toDate(trend.daily.end).getUTCFullYear()}`,
    footnote: "Sentiment is model-predicted.",
  },
  quarterly: {
    ...(trend.quarterly as Pick<View, "categories" | "series" | "start" | "end">),
    chart: "bar",
    unit: "quarter",
    tick: (p) => `Q${qNum(p)} ${qYear(p)}`,
    periodTitle: (p) => `${QUARTER_MONTHS[qNum(p) - 1]} ${qYear(p)}`,
    firstHeader: "Quarter",
    title: (subject) => `Sentiment towards ${subject} before this week, quarter by quarter`,
    subtitle: (n) =>
      `Share of the most-engaged posts per quarter · ${n.toLocaleString()} posts, ${monthYearFmt.format(toDate(trend.quarterly.start))} to ${dayMonthFmt.format(toDate(trend.quarterly.end))} ${toDate(trend.quarterly.end).getUTCFullYear()}`,
    footnote:
      "Before this week only the most-engaged posts on X were collected, about 50 a quarter, so this shows sentiment in viral posts rather than the everyday conversation. Sentiment is model-predicted.",
  },
};

const axisTick = { fontSize: 12, fontWeight: 600, fill: "#8A95A1" };
const card: CSSProperties = { background: "#fff", borderRadius: 22, padding: "22px 24px 18px", boxShadow: "0 3px 14px rgba(18,24,31,.06)" };
const cardTitle: CSSProperties = { margin: "0 0 4px", fontSize: 19, fontWeight: 800, letterSpacing: "-.02em", color: "#12181F" };
const cardSub: CSSProperties = { margin: 0, fontSize: 13.5, fontWeight: 500, color: "#6B7684" };
const footnote: CSSProperties = { margin: "10px 0 0", fontSize: 12.5, fontWeight: 500, color: "#9AA5B1" };

function BucketTooltip({ title, bucket }: { title: string; bucket?: Bucket }) {
  if (!bucket) return null;
  return (
    <div style={{ background: "#fff", borderRadius: 14, padding: "12px 14px", boxShadow: "0 6px 24px rgba(18,24,31,.14)", minWidth: 180 }}>
      <div style={{ fontSize: 13, fontWeight: 800, color: "#12181F", marginBottom: 8 }}>{title}</div>
      {plotted(bucket) ? (
        [...SERIES].reverse().map((s) => (
          <div key={s.key} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, fontWeight: 600, color: "#2A3440", padding: "2px 0" }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: s.color, flex: "none" }}></span>
            <span style={{ flex: 1 }}>{s.label}</span>
            <span style={{ fontWeight: 800 }}>{bucket[s.key]}%</span>
          </div>
        ))
      ) : (
        <div style={{ fontSize: 13, fontWeight: 600, color: "#6B7684" }}>
          {bucket.n === 0 ? "No posts collected" : `Only ${bucket.n} posts, too few to plot`}
        </div>
      )}
      <div style={{ fontSize: 12, fontWeight: 600, color: "#9AA5B1", marginTop: 8 }}>{bucket.n.toLocaleString()} posts</div>
    </div>
  );
}

function Legend({ shares }: { shares?: Bucket }) {
  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
      {[...SERIES].reverse().map((s) => (
        <span key={s.key} style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 13, fontWeight: 700, color: "#2A3440" }}>
          <span style={{ width: 11, height: 11, borderRadius: 3, background: s.color }}></span>
          {s.label}
          {shares && plotted(shares) && <span style={{ color: "#9AA5B1", fontWeight: 600 }}>{shares[s.key]}%</span>}
        </span>
      ))}
    </div>
  );
}

function SentimentBars({ layout }: { layout: "horizontal" | "vertical" }) {
  return SERIES.map((s, i) => (
    <Bar
      key={s.key}
      dataKey={s.key}
      name={s.label}
      stackId="sentiment"
      fill={s.color}
      stroke="#fff"
      strokeWidth={1}
      radius={i === SERIES.length - 1 ? (layout === "horizontal" ? [4, 4, 0, 0] : [0, 4, 4, 0]) : 0}
      isAnimationActive={false}
    />
  ));
}

function SentimentLines() {
  return SERIES.map((s) => (
    <Line
      key={s.key}
      type="monotone"
      dataKey={s.key}
      name={s.label}
      stroke={s.color}
      strokeWidth={2.5}
      dot={false}
      activeDot={{ r: 4.5, strokeWidth: 2, stroke: "#fff" }}
      isAnimationActive={false}
    />
  ));
}

// Shares never come near 100% on their own, so the line chart's axis stops at the
// next 10% above the highest value (at least 50%) instead of wasting half the height.
function lineAxisTicks(data: Period[]) {
  const max = Math.max(...data.flatMap((b) => SERIES.map((s) => b[s.key] ?? 0)));
  const top = Math.max(50, Math.ceil(max / 10) * 10);
  return Array.from({ length: top / 10 + 1 }, (_, i) => i * 10);
}

function ShareTable({ rows, firstHeader }: { rows: { key: string; label: string; bucket: Bucket }[]; firstHeader: string }) {
  return (
    <details style={{ marginTop: 12 }}>
      <summary style={{ cursor: "pointer", fontSize: 13, fontWeight: 700, color: "#6B7684" }}>View as table</summary>
      <table style={{ width: "100%", marginTop: 10, borderCollapse: "collapse", fontSize: 13, color: "#2A3440" }}>
        <thead>
          <tr style={{ textAlign: "right", color: "#8A95A1" }}>
            <th style={{ textAlign: "left", padding: "6px 4px" }}>{firstHeader}</th>
            <th style={{ padding: "6px 4px" }}>Posts</th>
            {SERIES.map((s) => (
              <th key={s.key} style={{ padding: "6px 4px" }}>{s.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key} style={{ textAlign: "right", borderTop: "1px solid #EEF1F4" }}>
              <td style={{ textAlign: "left", padding: "6px 4px", fontWeight: 600 }}>{r.label}</td>
              <td style={{ padding: "6px 4px" }}>{r.bucket.n.toLocaleString()}</td>
              {SERIES.map((s) => (
                <td key={s.key} style={{ padding: "6px 4px" }}>{plotted(r.bucket) ? `${r.bucket[s.key]}%` : "-"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

function Segmented<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: { value: T; label: string; disabled?: boolean; title?: string }[];
  value: T;
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div role="group" aria-label={label} style={{ display: "flex", gap: 4, flexWrap: "wrap", background: "#EEF1F4", padding: 4, borderRadius: 12 }}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            disabled={o.disabled}
            title={o.title}
            onClick={() => onChange(o.value)}
            style={{
              border: 0,
              fontSize: 13,
              fontWeight: 700,
              padding: "6px 12px",
              borderRadius: 9,
              cursor: o.disabled ? "not-allowed" : "pointer",
              background: on ? "#fff" : "transparent",
              color: o.disabled ? "#C3CCD5" : on ? "#12181F" : "#6B7684",
              boxShadow: on ? "0 1px 4px rgba(18,24,31,.12)" : "none",
            }}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

export default function SentimentTrendChart({ view: viewId }: { view: ViewId }) {
  const view = VIEWS[viewId];
  const [category, setCategory] = useState<CategoryId>("all");

  const data = view.series[category];
  const selected = view.categories.find((c) => c.id === category)!;
  const shown = data.filter(plotted).length;
  const subject = category === "all" ? "vaccines" : `${selected.label} vaccines`;

  const tooltip = (p: { active?: boolean; payload?: ReadonlyArray<{ payload?: Period }> }) => {
    const b = p.payload?.[0]?.payload;
    return p.active && b ? <BucketTooltip title={view.periodTitle(b.period)} bucket={b} /> : null;
  };

  // Only offer diseases with enough posts to plot most periods
  const options = view.categories
    .filter((c) => view.series[c.id].filter(plotted).length * 2 >= view.series[c.id].length)
    .map((c) => ({ value: c.id, label: c.label }));

  return (
    <section style={card}>
      {options.length > 1 && (
        <div style={{ marginBottom: 20 }}>
          <Segmented label="Disease" options={options} value={category} onChange={setCategory} />
        </div>
      )}

      <div style={{ display: "flex", alignItems: "flex-end", gap: 16, flexWrap: "wrap", marginBottom: 18 }}>
        <div style={{ flex: 1, minWidth: 240 }}>
          <h3 style={cardTitle}>{view.title(subject)}</h3>
          <p style={cardSub}>{view.subtitle(selected.n)}</p>
        </div>
        <Legend shares={selected} />
      </div>

      <div style={{ width: "100%", height: 280 }}>
        <ResponsiveContainer>
          {view.chart === "line" ? (
            <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
              <CartesianGrid vertical={false} stroke="#EEF1F4" />
              <XAxis dataKey="period" tickFormatter={view.tick} interval={0} tickLine={false} axisLine={{ stroke: "#DCE4EA" }} tick={axisTick} padding={{ left: 6, right: 6 }} />
              <YAxis domain={[0, "dataMax"]} ticks={lineAxisTicks(data)} tickFormatter={(v: number) => `${v}%`} tickLine={false} axisLine={false} tick={axisTick} />
              <Tooltip cursor={{ stroke: "#C3CCD5", strokeDasharray: "3 3" }} content={tooltip} />
              {SentimentLines()}
            </LineChart>
          ) : (
            <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -12 }} barCategoryGap="22%">
              <CartesianGrid vertical={false} stroke="#EEF1F4" />
              <XAxis dataKey="period" tickFormatter={view.tick} interval={0} tickLine={false} axisLine={{ stroke: "#DCE4EA" }} tick={axisTick} />
              <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(v: number) => `${v}%`} tickLine={false} axisLine={false} tick={axisTick} />
              <Tooltip cursor={{ fill: "rgba(18,24,31,.05)" }} content={tooltip} />
              {SentimentBars({ layout: "horizontal" })}
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>

      <p style={footnote}>
        {shown < data.length &&
          (view.chart === "line" ? `Gaps are ${view.unit}s with fewer than ${MIN_N} posts. ` : `Empty ${view.unit}s had fewer than ${MIN_N} posts. `)}
        {view.footnote}
      </p>

      <ShareTable
        firstHeader={view.firstHeader}
        rows={data.filter((b) => b.n > 0).map((b) => ({ key: b.period, label: view.periodTitle(b.period), bucket: b }))}
      />
    </section>
  );
}

// Overall split per disease, most negative first, with all vaccines as the reference row.
const OVERALL = trend.overall as Category[];
const BY_DISEASE = [
  OVERALL.find((c) => c.id === "all")!,
  ...OVERALL.filter((c) => c.id !== "all" && plotted(c)).sort((a, b) => b.negative! - a.negative!),
];

function DiseaseTick({ x, y, payload }: { x?: number | string; y?: number | string; payload?: { value: string } }) {
  const c = BY_DISEASE.find((v) => v.label === payload?.value);
  if (!c) return null;
  return (
    <g transform={`translate(${Number(x) - 8},${Number(y)})`}>
      <text textAnchor="end" dy={-2} style={{ fontSize: 13, fontWeight: c.id === "all" ? 800 : 700, fill: "#2A3440" }}>
        {c.label}
      </text>
      <text textAnchor="end" dy={13} style={{ fontSize: 11.5, fontWeight: 600, fill: "#9AA5B1" }}>
        {c.n.toLocaleString()} posts
      </text>
    </g>
  );
}

export function SentimentByDisease() {
  return (
    <section style={card}>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 16, flexWrap: "wrap", marginBottom: 14 }}>
        <div style={{ flex: 1, minWidth: 240 }}>
          <h3 style={cardTitle}>Sentiment by disease</h3>
          <p style={cardSub}>
            Share of posts about each disease&apos;s vaccine, {monthYearFmt.format(toDate(trend.quarterly.start))} to{" "}
            {dayMonthFmt.format(toDate(trend.daily.end))} {toDate(trend.daily.end).getUTCFullYear()}
          </p>
        </div>
        <Legend />
      </div>

      <div style={{ width: "100%", height: BY_DISEASE.length * 46 + 30 }}>
        <ResponsiveContainer>
          <BarChart data={BY_DISEASE} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 0 }} barCategoryGap="26%">
            <CartesianGrid horizontal={false} stroke="#EEF1F4" />
            <XAxis type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(v: number) => `${v}%`} tickLine={false} axisLine={false} tick={axisTick} />
            <YAxis type="category" dataKey="label" width={118} tickLine={false} axisLine={false} interval={0} tick={DiseaseTick} />
            <Tooltip
              cursor={{ fill: "rgba(18,24,31,.05)" }}
              content={(p) => {
                const c = (p.payload as ReadonlyArray<{ payload?: Category }> | undefined)?.[0]?.payload;
                return p.active && c ? <BucketTooltip title={c.label} bucket={c} /> : null;
              }}
            />
            {SentimentBars({ layout: "vertical" })}
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p style={footnote}>
        Matched by disease or vaccine name in the post text; a post naming two diseases counts for both. MMR covers measles, mumps and
        rubella. Most posts are from this week.
      </p>

      <ShareTable firstHeader="Disease" rows={BY_DISEASE.map((c) => ({ key: c.id, label: c.label, bucket: c }))} />
    </section>
  );
}
