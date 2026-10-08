const API_URL = process.env.API_URL ?? "http://localhost:8000";

export type SentimentLabel = "positive" | "neutral" | "negative";

// Mirrors the dict returned by backend/main_api/x_post_fetcher.py.
// Fields the syndication fallback can't supply come back as null.
export type XPost = {
  id: string;
  url: string;
  created_at: string | null;
  text: string;
  lang: string | null;
  author_name: string | null;
  author_handle: string | null;
  likes: number | null;
  reposts: number | null;
  replies: number | null;
  quotes: number | null;
  views: number | null;
  reply_to_handle: string | null;
  is_quote: boolean;
  media_count: number;
  media_urls: string[];
  has_community_note: boolean | null;
  _backend: string;
};

// Fields every /analyse/* endpoint returns alongside its model's label and scores
interface Analysis<L extends string> {
  query: string;
  // The text the model scored: the query itself, or the fetched post's text
  text: string;
  // The fetched post when the query was a post URL, otherwise null
  post: XPost | null;
  label: L;
  // Model confidence in each label, 0 to 1, summing to 1
  scores: Record<L, number>;
}

export type SentimentAnalysis = Analysis<SentimentLabel>;

export type MisinformationLabel = "misinformation" | "not_misinformation";
export type MisinformationAnalysis = Analysis<MisinformationLabel>;

type AnalysisResult<A> =
  | { ok: true; analysis: A }
  // invalidInput: the query itself is the problem (not an X post link, post not found),
  // as opposed to the backend or model being down
  | { ok: false; error: string; invalidInput: boolean };

export type SentimentResult = AnalysisResult<SentimentAnalysis>;
export type MisinformationResult = AnalysisResult<MisinformationAnalysis>;

// Never throws, so the page still renders when the backend, model or post fetch fails.
async function analyse<A>(endpoint: string, modelName: string, query: string): Promise<AnalysisResult<A>> {
  try {
    const res = await fetch(`${API_URL}/analyse/${endpoint}?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    if (!res.ok) {
      // FastAPI puts the message from HTTPException in `detail`
      if (res.status >= 400 && res.status < 500) {
        const error = typeof data.detail === "string" ? data.detail : "That input can't be analysed. Try a claim or a link to an X post.";
        return { ok: false, error, invalidInput: true };
      }
      return {
        ok: false,
        error: `Couldn't reach the ${modelName} model. Check that the backend and model service are running and try again.`,
        invalidInput: false,
      };
    }
    return { ok: true, analysis: data };
  } catch {
    return { ok: false, error: "Couldn't reach the backend. Check that the API is running and try again.", invalidInput: false };
  }
}

export function analyseSentiment(query: string): Promise<SentimentResult> {
  return analyse("sentiment", "sentiment", query);
}

export function analyseMisinformation(query: string): Promise<MisinformationResult> {
  return analyse("misinformation", "misinformation", query);
}

// Plain-language reason for the misinformation label, from a local LLM. Slow (~10s),
// so the result page streams it in after the scores. Null when the LLM is unavailable.
export async function explainMisinformation(analysis: MisinformationAnalysis): Promise<string | null> {
  try {
    const res = await fetch(`${API_URL}/analyse/misinformation/explanation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: analysis.text, label: analysis.label }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return typeof data.explanation === "string" ? data.explanation : null;
  } catch {
    return null;
  }
}
