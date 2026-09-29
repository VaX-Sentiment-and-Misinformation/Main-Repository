const API_URL = process.env.API_URL ?? "http://localhost:8000";

export type SentimentLabel = "positive" | "neutral" | "negative";

export interface SentimentAnalysis {
  query: string;
  matched: number;
  analysed: number;
  // "stored" means the model service was down and saved predictions were used
  source: "model" | "stored" | null;
  sentiment: Record<SentimentLabel, { count: number; pct: number }>;
}

// Returns null when the backend can't be reached, so the page still renders.
export async function analyseSentiment(query: string): Promise<SentimentAnalysis | null> {
  try {
    const res = await fetch(`${API_URL}/analyse/sentiment?q=${encodeURIComponent(query)}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}
