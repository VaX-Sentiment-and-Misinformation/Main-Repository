import { explainMisinformation, type MisinformationAnalysis } from "@/lib/api";

// The prompt (kept identical to the team's trial.py) makes the LLM open by restating the label, e.g.
// 'This statement fits the classification of MISINFORMATION because it ...'. The page already shows
// the verdict, so drop that opening for display. Text that doesn't start this way is left as is.
const LABEL_PREAMBLE =
  /^\s*(?:this|the)\s+statement\s+(?:"[^"]*"\s+)?(?:fits\s+(?:the\s+)?classification\s+(?:of\s+)?|is\s+classified\s+as\s+)(?:NOT_)?MISINFORMATION\s+(?:because|since|as)\s+/i;

export function withoutLabelPreamble(text: string): string {
  const rest = text.replace(LABEL_PREAMBLE, "");
  if (rest === text || !rest) return text;
  return rest[0].toUpperCase() + rest.slice(1);
}

// Async server component: render inside <Suspense> so the rest of the result page doesn't wait for the LLM.
export default async function MisinformationExplanation({ analysis }: { analysis: MisinformationAnalysis }) {
  const explanation = await explainMisinformation(analysis);
  if (!explanation) return <div style={{ color: "#9AA5B1" }}>Explanation unavailable right now.</div>;
  return <div>{withoutLabelPreamble(explanation)}</div>;
}

export function ExplanationSkeleton() {
  return (
    <div role="status" aria-label="Generating explanation">
      <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
        <div className="vx-skeleton" style={{ width: "100%" }}></div>
        <div className="vx-skeleton" style={{ width: "92%" }}></div>
        <div className="vx-skeleton" style={{ width: "58%" }}></div>
      </div>
      <div style={{ marginTop: 12, fontSize: 12.5, fontWeight: 600, color: "#9AA5B1" }}>Generating explanation...</div>
    </div>
  );
}
