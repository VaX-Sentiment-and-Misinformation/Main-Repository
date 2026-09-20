"use client";

import { useState, type CSSProperties } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import trend from "@/data/sentimentTrend.json";

type Sentiment = "negative" | "neutral" | "positive";
type Granularity = "weekly" | "monthly";
type CategoryId = keyof typeof trend.series.weekly;

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

const CATEGORIES = trend.categories as Category[];
const SERIES_BY: Record<Granularity, Record<CategoryId, Period[]>> = trend.series;
const MIN_N = trend.minBucketTweets;

const plotted = (b: Bucket) => b.negative !== undefined;
const plottedCount = (g: Granularity, c: CategoryId) => SERIES_BY[g][c].filter(plotted).length;

const dayFmt = new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
const monthFmt = new Intl.DateTimeFormat("en-AU", { month: "short", timeZone: "UTC" });
const monthYearFmt = new Intl.DateTimeFormat("en-AU", { month: "long", year: "numeric", timeZone: "UTC" });

const toDate = (period: string) => new Date(`${period}T00:00:00Z`);
const periodTitle = (g: Granularity, period: string) =>
  g === "weekly" ? `Week of ${dayFmt.format(toDate(period))}` : monthYearFmt.format(toDate(period));

// Label the first week of each month, skipping any label within 3 bars of the previous
// one so a partial first month doesn't collide with the next. Years are in the subtitle.
const WEEK_TICKS = (() => {
  const weeks = SERIES_BY.weekly.all;
  const labels = new Map<string, string>();
  let lastIndex = -Infinity;
  weeks.forEach((w, i) => {
    const d = toDate(w.period);
    if (i > 0 && toDate(weeks[i - 1].period).getUTCMonth() === d.getUTCMonth()) return;
    if (i - lastIndex < 3) labels.delete(weeks[lastIndex].period);
    labels.set(w.period, monthFmt.format(d));
    lastIndex = i;
  });
  return labels;
})();

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
          {bucket.n === 0 ? "No tweets collected" : `Only ${bucket.n} tweets, too few to plot`}
        </div>
      )}
      <div style={{ fontSize: 12, fontWeight: 600, color: "#9AA5B1", marginTop: 8 }}>{bucket.n.toLocaleString()} tweets</div>
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

function ShareTable({ rows, firstHeader }: { rows: { key: string; label: string; bucket: Bucket }[]; firstHeader: string }) {
  return (
    <details style={{ marginTop: 12 }}>
      <summary style={{ cursor: "pointer", fontSize: 13, fontWeight: 700, color: "#6B7684" }}>View as table</summary>
      <table style={{ width: "100%", marginTop: 10, borderCollapse: "collapse", fontSize: 13, color: "#2A3440" }}>
        <thead>
          <tr style={{ textAlign: "right", color: "#8A95A1" }}>
            <th style={{ textAlign: "left", padding: "6px 4px" }}>{firstHeader}</th>
            <th style={{ padding: "6px 4px" }}>Tweets</th>
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

export default function SentimentTrendChart() {
  const [category, setCategory] = useState<CategoryId>("all");
  const [granularity, setGranularity] = useState<Granularity>("weekly");

  const data = SERIES_BY[granularity][category];
  const selected = CATEGORIES.find((c) => c.id === category)!;
  const shown = data.filter(plotted).length;
  const first = toDate(data[0].period);
  const last = toDate(data[data.length - 1].period);

  const categoryOptions = CATEGORIES.map((c) => {
    const chartable = plottedCount("monthly", c.id) > 0;
    return {
      value: c.id,
      label: c.label,
      disabled: !chartable,
      title: chartable ? undefined : `Only ${c.n} tweets, never ${MIN_N}+ in one month. Compare it in the chart below.`,
    };
  });

  return (
    <section style={card}>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 20 }}>
        <Segmented label="Vaccine" options={categoryOptions} value={category} onChange={setCategory} />
        <Segmented
          label="Time period"
          options={[
            { value: "weekly", label: "Weekly" },
            { value: "monthly", label: "Monthly" },
          ]}
          value={granularity}
          onChange={setGranularity}
        />
      </div>

      <div style={{ display: "flex", alignItems: "flex-end", gap: 16, flexWrap: "wrap", marginBottom: 18 }}>
        <div style={{ flex: 1, minWidth: 240 }}>
          <h3 style={cardTitle}>
            {category === "all" ? "Sentiment towards vaccines" : `Sentiment towards ${selected.label}`}, {granularity === "weekly" ? "week by week" : "month by month"}
          </h3>
          <p style={cardSub}>
            Share of tweets per {granularity === "weekly" ? "week" : "month"} · {selected.n.toLocaleString()} tweets, {monthFmt.format(first)}{" "}
            {first.getUTCFullYear()} to {monthFmt.format(last)} {last.getUTCFullYear()}
          </p>
        </div>
        <Legend shares={selected} />
      </div>

      <div style={{ width: "100%", height: 300 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -12 }} barCategoryGap={granularity === "weekly" ? 3 : "22%"}>
            <CartesianGrid vertical={false} stroke="#EEF1F4" />
            <XAxis
              dataKey="period"
              tickFormatter={(p: string) => (granularity === "weekly" ? (WEEK_TICKS.get(p) ?? "") : monthFmt.format(toDate(p)))}
              interval={0}
              tickLine={false}
              axisLine={{ stroke: "#DCE4EA" }}
              tick={axisTick}
            />
            <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(v: number) => `${v}%`} tickLine={false} axisLine={false} tick={axisTick} />
            <Tooltip
              cursor={{ fill: "rgba(18,24,31,.05)" }}
              content={(p) => {
                const b = (p.payload as ReadonlyArray<{ payload?: Period }> | undefined)?.[0]?.payload;
                return p.active && b ? <BucketTooltip title={periodTitle(granularity, b.period)} bucket={b} /> : null;
              }}
            />
            {SentimentBars({ layout: "horizontal" })}
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p style={footnote}>
        {granularity === "weekly" && shown < data.length / 2 && plottedCount("monthly", category) > shown
          ? `Only ${shown} of ${data.length} weeks have ${MIN_N}+ ${category === "all" ? "" : `${selected.label} `}tweets. Monthly shows more. `
          : ""}
        Empty {granularity === "weekly" ? "weeks" : "months"} had no tweets collected or fewer than {MIN_N}. Sentiment is model-predicted.
      </p>

      <ShareTable
        firstHeader={granularity === "weekly" ? "Week of" : "Month"}
        rows={data
          .filter((b) => b.n > 0)
          .map((b) => ({
            key: b.period,
            label: granularity === "weekly" ? dayFmt.format(toDate(b.period)) : monthYearFmt.format(toDate(b.period)),
            bucket: b,
          }))}
      />
    </section>
  );
}

// Overall split per vaccine, most negative first, with all vaccines as the reference row.
const BY_VACCINE = [
  CATEGORIES.find((c) => c.id === "all")!,
  ...CATEGORIES.filter((c) => c.id !== "all" && plotted(c)).sort((a, b) => b.negative! - a.negative!),
];

function VaccineTick({ x, y, payload }: { x?: number | string; y?: number | string; payload?: { value: string } }) {
  const c = BY_VACCINE.find((v) => v.label === payload?.value);
  if (!c) return null;
  return (
    <g transform={`translate(${Number(x) - 8},${Number(y)})`}>
      <text textAnchor="end" dy={-2} style={{ fontSize: 13, fontWeight: c.id === "all" ? 800 : 700, fill: "#2A3440" }}>
        {c.label}
      </text>
      <text textAnchor="end" dy={13} style={{ fontSize: 11.5, fontWeight: 600, fill: "#9AA5B1" }}>
        {c.n.toLocaleString()} tweets
      </text>
    </g>
  );
}

export function SentimentByVaccine() {
  return (
    <section style={card}>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 16, flexWrap: "wrap", marginBottom: 14 }}>
        <div style={{ flex: 1, minWidth: 240 }}>
          <h3 style={cardTitle}>Sentiment by vaccine</h3>
          <p style={cardSub}>Share of tweets naming each COVID-19 vaccine, whole period</p>
        </div>
        <Legend />
      </div>

      <div style={{ width: "100%", height: BY_VACCINE.length * 46 + 30 }}>
        <ResponsiveContainer>
          <BarChart data={BY_VACCINE} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 0 }} barCategoryGap="26%">
            <CartesianGrid horizontal={false} stroke="#EEF1F4" />
            <XAxis type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickFormatter={(v: number) => `${v}%`} tickLine={false} axisLine={false} tick={axisTick} />
            <YAxis type="category" dataKey="label" width={118} tickLine={false} axisLine={false} interval={0} tick={VaccineTick} />
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
        Matched by name in the tweet text; a tweet naming two vaccines counts for both. AstraZeneca includes Oxford and Covishield. Other brands:
        Sinovac, Sinopharm, Covaxin, Sputnik, Novavax.
      </p>

      <ShareTable firstHeader="Vaccine" rows={BY_VACCINE.map((c) => ({ key: c.id, label: c.label, bucket: c }))} />
    </section>
  );
}
