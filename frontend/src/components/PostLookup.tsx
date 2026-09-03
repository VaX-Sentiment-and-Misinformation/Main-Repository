"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

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
  backend: string | null;
  fetched_at: string;
  // true when the row came from the database rather than a fresh fetch
  _cached: boolean;
};

export default function PostLookup() {
  const [url, setUrl] = useState("");
  const [post, setPost] = useState<XPost | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setPost(null);

    try {
      const res = await fetch(`${API_URL}/api/post`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      const data = await res.json();
      if (!res.ok) {
        // FastAPI puts the message from HTTPException in `detail`.
        setError(typeof data.detail === "string" ? data.detail : "Request failed");
        return;
      }
      setPost(data as XPost);
    } catch {
      setError("Could not reach the backend. Is the API running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-xl">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="url"
          required
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://x.com/user/status/123..."
          className="flex-1 rounded border border-gray-300 px-3 py-2"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
        >
          {loading ? "Fetching..." : "Analyse"}
        </button>
      </form>

      {error && <p className="mt-4 text-red-600">{error}</p>}

      {post && (
        <article className="mt-6 rounded border border-gray-300 p-4">
          <p className="font-semibold">
            {post.author_name}{" "}
            <span className="font-normal text-gray-500">@{post.author_handle}</span>
          </p>
          <p className="mt-2 whitespace-pre-wrap">{post.text}</p>
          <p className="mt-3 text-sm text-gray-500">
            {post.created_at} · {post.likes ?? "-"} likes · {post.reposts ?? "-"} reposts
          </p>
        </article>
      )}
    </div>
  );
}
