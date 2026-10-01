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
  views: number | null;
  media_urls: string[];
  _backend: string;
};

export interface SentimentAnalysis {
  query: string;
  // The text the model scored: the query itself, or the fetched post's text
  text: string;
  // The fetched post when the query was a post URL, otherwise null
  post: XPost | null;
  label: SentimentLabel;
  // Model confidence in each label, 0 to 1, summing to 1
  scores: Record<SentimentLabel, number>;
}

export type SentimentResult =
  | { ok: true; analysis: SentimentAnalysis }
  // invalidInput: the query itself is the problem (not an X post link, post not found),
  // as opposed to the backend or model being down
  | { ok: false; error: string; invalidInput: boolean };

// Never throws, so the page still renders when the backend, model or post fetch fails.
export async function analyseSentiment(query: string): Promise<SentimentResult> {
  try {
    const res = await fetch(`${API_URL}/analyse/sentiment?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    if (!res.ok) {
      // FastAPI puts the message from HTTPException in `detail`
      if (res.status >= 400 && res.status < 500) {
        const error = typeof data.detail === "string" ? data.detail : "That input can't be analysed. Try a claim or a link to an X post.";
        return { ok: false, error, invalidInput: true };
      }
      return {
        ok: false,
        error: "Couldn't reach the sentiment model. Check that the backend and model service are running and try again.",
        invalidInput: false,
      };
    }
    return { ok: true, analysis: data };
  } catch {
    return { ok: false, error: "Couldn't reach the backend. Check that the API is running and try again.", invalidInput: false };
  }
}
