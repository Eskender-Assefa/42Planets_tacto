import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { useCase, useSuppliers } from "@/lib/command";
import { buildBriefingScript, type BriefingMode } from "@/lib/briefing";
import { useSpeech } from "@/hooks/useSpeech";
import { SpeechControls } from "@/components/SpeechControls";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/briefing/$sessionId")({
  head: ({ params }) => ({
    meta: [
      { title: `Voice Briefing ${params.sessionId} · Hollerau Agentic Command` },
      { name: "description", content: "Listen to a spoken summary of how the agent structured its trade-offs." },
      { property: "og:title", content: `Voice Briefing ${params.sessionId} · Hollerau Agentic Command` },
      { property: "og:description", content: "Listen to a spoken summary of how the agent structured its trade-offs." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Briefing,
});

function Briefing() {
  const { sessionId } = Route.useParams();
  const { c, logs } = useCase(sessionId);
  const suppliers = useSuppliers();
  const [mode, setMode] = useState<BriefingMode>("summary");
  const k = c.data;
  const sentences = k ? buildBriefingScript(k, logs.data ?? [], (id) => suppliers.data?.get(id)?.name ?? "", mode) : [];
  const speech = useSpeech(sentences);
  useEffect(() => { speech.stop(); }, [sessionId, speech.stop]);

  return (
    <Shell>
      <Link to="/audit/$sessionId" params={{ sessionId }} className="num text-xs text-muted-foreground hover:text-foreground">← Audit</Link>
      <div className="mx-auto mt-8 max-w-2xl text-center">
        <div className="label-caps">D · Voice briefing room</div>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight">{k ? (k.title ?? k.case_id) : "…"}</h1>
        <div className="my-6 flex justify-center gap-2">{(["summary", "full"] as const).map((value) => <Button key={value} variant={mode === value ? "default" : "outline"} aria-pressed={mode === value} onClick={() => setMode(value)}>{value === "summary" ? "Summary" : "Full negotiation"}</Button>)}</div>
        {sentences.length > 0 && <SpeechControls speech={speech} large />}
        {(logs.isError || c.isError) && <p role="alert" className="mt-6 text-destructive">Briefing data could not be loaded.</p>}
        <ol className="mt-8 space-y-2 text-left">{sentences.map((sentence, i) => <li key={`${i}-${sentence}`}><Button variant="ghost" aria-current={speech.current === i ? "true" : undefined} onClick={() => { if (speech.supported) speech.play(i); }} className={`h-auto w-full justify-start whitespace-normal p-3 text-left leading-relaxed ${speech.current === i ? "bg-accent text-accent-foreground" : "text-muted-foreground"}`}>{sentence}</Button></li>)}</ol>
        {!sentences.length && <p className="mt-8 text-muted-foreground">{logs.isLoading || c.isLoading ? "Loading briefing…" : "-"}</p>}
      </div>
    </Shell>
  );
}
