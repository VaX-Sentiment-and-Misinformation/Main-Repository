import { Suspense } from "react";
import MisinformationExplanation, { ExplanationSkeleton } from "@/components/MisinformationExplanation";
import Result from "@/pages/result/result";
import { analyseMisinformation, analyseSentiment } from "@/lib/api";
import { DEFAULT_QUERY } from "@/lib/mockData";

export default async function Page({ searchParams }: PageProps<"/result">) {
  const { q } = await searchParams;
  const query = (Array.isArray(q) ? q[0] : q)?.trim() || DEFAULT_QUERY;
  const [result, misinformation] = await Promise.all([analyseSentiment(query), analyseMisinformation(query)]);

  // Streams in after the scores, since the explanation LLM takes ~10s
  const explanation = misinformation.ok && (
    <Suspense fallback={<ExplanationSkeleton />}>
      <MisinformationExplanation analysis={misinformation.analysis} />
    </Suspense>
  );

  return <Result query={query} result={result} misinformation={misinformation} explanation={explanation} />;
}
