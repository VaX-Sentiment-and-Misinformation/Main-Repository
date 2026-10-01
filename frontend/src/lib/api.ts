const API_URL = process.env.API_URL ?? "http://localhost:8000";

export type SentimentLabel = "positive" | "neutral" | "negative";

export interface SentimentAnalysis {
  query: string;
  label: SentimentLabel;
  // Model confidence in each label, 0 to 1, summing to 1
  scores: Record<SentimentLabel, number>;
}

// Returns null when the backend or model can't be reached, so the page still renders.
export async function analyseSentiment(query: string): Promise<SentimentAnalysis | null> {
  try {
    const res = await fetch(`${API_URL}/analyse/sentiment?q=${encodeURIComponent(query)}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}
