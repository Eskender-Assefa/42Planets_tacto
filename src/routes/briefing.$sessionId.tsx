import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Shell } from "@/components/Shell";
import { useCase, useSuppliers, supplierNames, eur } from "@/lib/command";

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
  const [playing, setPlaying] = useState(false);
  const k = c.data;
  const last = logs.data?.at(-1);

  const script = k && last
    ? `Briefing for ${supplierNames(k, suppliers.data)}, turn ${last.turn_number}. Opening cost was ${eur(k.c_open)}; the latest supplier offer stands at ${eur(k.last_c_supplier_offer)} against a best of ${eur(k.c_best)}. ${last.strategic_intent} ${last.mathematical_justification}`
    : "";

  // Temporary browser voice until the ElevenLabs key is connected.
  const play = () => {
    if (!script || typeof window === "undefined") return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(script);
    u.onend = () => setPlaying(false);
    setPlaying(true);
    window.speechSynthesis.speak(u);
  };
  const stop = () => { window.speechSynthesis.cancel(); setPlaying(false); };

  return (
    <Shell>
      <Link to="/audit/$sessionId" params={{ sessionId }} className="num text-xs text-muted-foreground hover:text-foreground">← Audit</Link>
      <div className="mx-auto mt-8 max-w-2xl text-center">
        <div className="label-caps">D · Voice briefing room</div>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight">{k ? (k.title ?? k.case_id) : "…"}</h1>
        <button
          onClick={playing ? stop : play}
          disabled={!script}
          className={`mx-auto mt-10 grid h-32 w-32 place-items-center rounded-full bg-primary num text-sm font-bold uppercase tracking-widest text-primary-foreground disabled:opacity-40 ${playing ? "live" : ""}`}
        >
          {playing ? "Stop" : "Play"}
        </button>
        <p className="panel mt-10 p-6 text-left leading-relaxed text-muted-foreground">
          {script || (logs.isLoading || c.isLoading ? "Loading briefing…" : "No turns logged yet — start the runner.")}
        </p>
        <p className="mt-4 text-xs text-muted-foreground">Using the browser voice for now — ElevenLabs voice switches on once its key is added.</p>
      </div>
    </Shell>
  );
}
