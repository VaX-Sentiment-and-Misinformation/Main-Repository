"use client";

import { Fragment, useState, useSyncExternalStore } from "react";
import type { CSSProperties, MouseEvent, ReactNode } from "react";
import { COMPILED_ON, DISEASES, READ_FIRST, REGION_LABEL, REGION_SOURCE, US_STATUS, type Disease, type Region } from "@/lib/diseaseInfo";

const REGIONS: Region[] = ["au", "us", "who"];

// The selected disease lives in the URL hash so a disease can be linked to directly.
function subscribeHash(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}
const getHash = () => window.location.hash.slice(1);
const getServerHash = () => "";

function selectDisease(id: string) {
  history.replaceState(null, "", `#${id}`);
  window.dispatchEvent(new HashChangeEvent("hashchange"));
}

// Opens the notes in the footer without touching the hash, which holds the selected disease
function openAbout(e: MouseEvent) {
  e.preventDefault();
  const details = document.getElementById("about-details") as HTMLDetailsElement | null;
  if (!details) return;
  details.open = true;
  details.scrollIntoView({ behavior: "smooth", block: "center" });
}

// Renders **bold** segments from the content strings.
function rich(text: string): ReactNode {
  return text.split(/\*\*(.+?)\*\*/).map((part, i) => (i % 2 ? <strong key={i} style={{ color: "#12181F" }}>{part}</strong> : <Fragment key={i}>{part}</Fragment>));
}

export default function Info() {
  const hash = useSyncExternalStore(subscribeHash, getHash, getServerHash);
  const disease = DISEASES.find((d) => d.id === hash) ?? DISEASES[0];
  const [region, setRegion] = useState<Region>("au");

  return (
    <main className="vx-rise" style={{ maxWidth: 1180, margin: "0 auto", padding: "44px 40px 0" }}>
      <h1 style={{ fontSize: 42, fontWeight: 800, letterSpacing: "-.035em", margin: "0 0 10px" }}>Disease facts</h1>
      <p className="vx-text-pretty" style={{ color: "#6B7684", fontSize: 17, fontWeight: 500, lineHeight: 1.55, margin: "0 0 28px", maxWidth: 720 }}>
        The facts behind nine vaccine-preventable diseases and what health authorities recommend.
      </p>

      <Pills
        label="Disease"
        options={DISEASES.map((d) => ({ value: d.id, label: d.short }))}
        value={disease.id}
        onChange={selectDisease}
        style={{ marginBottom: 20 }}
      />

      <DiseasePanel disease={disease} region={region} onRegion={setRegion} />

      <footer style={{ maxWidth: 760, margin: "28px 4px 0" }}>
        <p className="vx-text-pretty" style={{ ...muted, margin: "0 0 10px" }}>
          General information only, not medical advice. Check dosing and eligibility in the{" "}
          <a href="https://immunisationhandbook.health.gov.au/" target="_blank" rel="noreferrer">
            Australian Immunisation Handbook
          </a>{" "}
          or with a health professional. Compiled {COMPILED_ON} from WHO, the US CDC and the Australian Department of Health,
          Disability and Ageing.
        </p>
        <details id="about-details" className="vx-acc">
          <summary style={{ ...muted, fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 6 }}>
            <Chevron /> About this information
          </summary>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
            {[...READ_FIRST, ...US_STATUS].map((t) => (
              <p key={t} className="vx-text-pretty" style={{ ...muted, margin: 0 }}>
                {rich(t)}
              </p>
            ))}
          </div>
        </details>
      </footer>
    </main>
  );
}

function DiseasePanel({ disease, region, onRegion }: { disease: Disease; region: Region; onRegion: (r: Region) => void }) {
  return (
    <article key={disease.id} className="vx-rise" style={{ background: "#fff", borderRadius: 22, padding: "30px 32px", boxShadow: "0 3px 14px rgba(18,24,31,.06)" }}>
      <h2 style={{ fontSize: 28, fontWeight: 800, letterSpacing: "-.03em", margin: "0 0 6px" }}>{disease.name}</h2>
      <p className="vx-text-pretty" style={{ fontSize: 17, lineHeight: 1.5, fontWeight: 600, color: "#0B7A5C", margin: "0 0 24px", maxWidth: 720 }}>
        {disease.headline}
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(360px, 100%), 1fr))", gap: "28px 44px", alignItems: "start" }}>
        <div>
          <dl style={{ display: "grid", gridTemplateColumns: "minmax(90px, 150px) minmax(0, 1fr)", margin: "0 0 18px" }}>
            {disease.facts.map(([k, v]) => (
              <Fragment key={k}>
                <dt style={{ ...factCell, fontWeight: 700, color: "#8A95A1" }}>{k}</dt>
                <dd style={{ ...factCell, margin: 0, fontWeight: 600, color: "#12181F" }}>{v}</dd>
              </Fragment>
            ))}
          </dl>

          {disease.sections.map((s, i) => (
            <details key={s.heading} className="vx-acc" open={i === 0} style={{ borderTop: "1px solid #EEF1F4" }}>
              <summary style={{ display: "flex", alignItems: "center", gap: 8, padding: "13px 0", fontSize: 15.5, fontWeight: 800, color: "#12181F" }}>
                <Chevron />
                {s.heading}
              </summary>
              <div style={{ padding: "0 0 16px 22px" }}>
                {s.paras?.map((p) => (
                  <p key={p} className="vx-text-pretty" style={{ ...body, margin: "0 0 10px" }}>
                    {rich(p)}
                  </p>
                ))}
                {s.bullets && (
                  <ul style={list}>
                    {s.bullets.map((b) => (
                      <li key={b}>{rich(b)}</li>
                    ))}
                  </ul>
                )}
              </div>
            </details>
          ))}
        </div>

        <aside style={{ background: "#F5F8F9", borderRadius: 18, padding: "20px 22px", position: "sticky", top: 84 }}>
          <h3 style={{ fontSize: 16, fontWeight: 800, letterSpacing: "-.01em", margin: "0 0 12px" }}>Vaccination advice</h3>
          <Pills
            label="Recommendations from"
            options={REGIONS.map((r) => ({ value: r, label: REGION_LABEL[r] }))}
            value={region}
            onChange={onRegion}
            fill
            style={{ marginBottom: 16, background: "#E4EAEE" }}
          />
          <ul style={list}>
            {disease.vaccination[region].map((v) => (
              <li key={v}>{rich(v)}</li>
            ))}
          </ul>
          <p style={{ ...muted, fontSize: 13, margin: "14px 0 0" }}>
            From: {REGION_SOURCE[region]}
            {region === "us" && (
              <>
                {" "}
                (
                <a href="#about" onClick={openAbout}>
                  why
                </a>
                )
              </>
            )}
            .
          </p>
          <p style={{ ...muted, fontSize: 13, margin: "12px 0 0", paddingTop: 12, borderTop: "1px solid #E4EAEE" }}>
            Sources:{" "}
            {disease.sources.map((s, i) => (
              <Fragment key={s.url}>
                {i > 0 && ", "}
                <a href={s.url} target="_blank" rel="noreferrer">
                  {s.label}
                </a>
              </Fragment>
            ))}
          </p>
        </aside>
      </div>
    </article>
  );
}

function Pills<T extends string>({
  label,
  options,
  value,
  onChange,
  fill,
  style,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
  fill?: boolean;
  style?: CSSProperties;
}) {
  return (
    <div role="group" aria-label={label} style={{ display: "flex", gap: 4, flexWrap: "wrap", background: "#E4EAEE", padding: 4, borderRadius: 13, width: fill ? undefined : "fit-content", ...style }}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(o.value)}
            style={{
              flex: fill ? 1 : undefined,
              border: 0,
              fontSize: 14,
              fontWeight: 700,
              padding: "7px 14px",
              borderRadius: 10,
              background: on ? "#fff" : "transparent",
              color: on ? "#12181F" : "#6B7684",
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

function Chevron() {
  return (
    <svg className="vx-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}>
      <path d="m9 6 6 6-6 6"></path>
    </svg>
  );
}

const body: CSSProperties = { fontSize: 15, lineHeight: 1.6, fontWeight: 500, color: "#2A3440" };
const list: CSSProperties = { ...body, margin: 0, paddingLeft: 18, listStyle: "disc", display: "flex", flexDirection: "column", gap: 7 };
const muted: CSSProperties = { fontSize: 13.5, lineHeight: 1.6, fontWeight: 500, color: "#8A95A1" };
const factCell: CSSProperties = { fontSize: 14, lineHeight: 1.5, padding: "7px 12px 7px 0" };
