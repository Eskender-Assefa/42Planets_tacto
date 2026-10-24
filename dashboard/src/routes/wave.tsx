import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Shell, MindsetBadge, StatusDot } from "@/components/Shell";
import { useCases, eur, clock, envelopeScore, type CaseRow } from "@/lib/command";

export const Route = createFileRoute("/wave")({
  head: () => ({
    meta: [
      { title: "Live Wave Terminal · Hollerau Agentic Command" },
      { name: "description", content: "Ten parallel negotiation cards with countdowns, cost envelopes and supplier mindset." },
      { property: "og:title", content: "Live Wave Terminal · Hollerau Agentic Command" },
      { property: "og:description", content: "Ten parallel negotiation cards with countdowns, cost envelopes and supplier mindset." },
    ],
  }),
  component: Wave,
});

const MAX_SECONDS = 600;

function Wave() {
  const { data = [] } = useCases();
  return (
    <Shell>
      <div className="mb-6 flex items-end justify-between">
        <div>
          <div className="label-caps">Wave 1 · parallel 10</div>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Live Wave Terminal</h1>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {data.map((c) => <WaveCard key={c.session_id} c={c} />)}
      </div>
    </Shell>
  );
}

function WaveCard({ c }: { c: CaseRow }) {
  const active = c.status === "Active";
  const [secs, setSecs] = useState(c.seconds_left);
  useEffect(() => setSecs(c.seconds_left), [c.seconds_left]);
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => setSecs((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, [active]);

  const open = Number(c.c_open), cur = Number(c.c_current_offer), floor = Number(c.c_best_floor);
  const score = active ? envelopeScore(open, cur, floor) : Number(c.final_score ?? c.current_score);
  const critical = active && secs < 60;
  const stalled = c.mindset === "Stalled";

  return (
    <Link
      to="/audit/$sessionId"
      params={{ sessionId: c.session_id }}
      className={`panel flex flex-col gap-4 p-4 transition hover:-translate-y-0.5 ${active ? "live" : "opacity-55"} ${stalled && active ? "border-warning" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-semibold leading-tight">{c.supplier?.name}</div>
          <div className="mt-0.5 text-xs text-muted-foreground">{c.supplier?.segment} · {c.supplier?.country}</div>
        </div>
        <StatusDot s={c.status} />
      </div>

      <div>
        <div className="flex justify-between">
          <span className="label-caps">Turn {c.turn_number}</span>
          <span className={`num text-sm ${critical ? "text-destructive" : ""}`}>{clock(secs)}</span>
        </div>
        <div className="mt-1 h-1 bg-muted">
          <div className={`h-full ${critical ? "bg-destructive" : "bg-primary"}`} style={{ width: `${Math.min(100, (secs / MAX_SECONDS) * 100)}%` }} />
        </div>
      </div>

      <div>
        <div className="label-caps mb-1">Cost envelope</div>
        <div className="relative h-2 bg-muted">
          <div className="absolute inset-y-0 left-0 bg-success/70" style={{ width: `${score * 100}%` }} />
        </div>
        <div className="mt-1 flex justify-between num text-[10px] text-muted-foreground">
          <span>{eur(open)}</span><span>{eur(floor)}</span>
        </div>
        <div className="mt-2 num text-lg text-primary">{eur(cur)}</div>
      </div>

      <div className="mt-auto flex items-center justify-between border-t border-border pt-3">
        <MindsetBadge m={c.mindset} />
        <span className="num text-2xl font-semibold">{score.toFixed(3)}</span>
      </div>
    </Link>
  );
}
