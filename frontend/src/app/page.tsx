import PostLookup from "@/components/PostLookup";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-24">
      <h1 className="text-4xl font-bold">Vaccine Post Analyser</h1>
      <PostLookup />
    </main>
  );
}
