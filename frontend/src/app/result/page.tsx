import Result from "@/pages/result/result";
import { analyseSentiment } from "@/lib/api";
import { DEFAULT_QUERY } from "@/lib/mockData";

export default async function Page({ searchParams }: PageProps<"/result">) {
  const { q } = await searchParams;
  const query = (Array.isArray(q) ? q[0] : q)?.trim() || DEFAULT_QUERY;
  const result = await analyseSentiment(query);

  return <Result query={query} result={result} />;
}
