import Result from "@/pages/result/result";

export default async function Page({ searchParams }: PageProps<"/result">) {
  const { q } = await searchParams;
  const query = Array.isArray(q) ? q[0] : q;

  return <Result query={query} />;
}
