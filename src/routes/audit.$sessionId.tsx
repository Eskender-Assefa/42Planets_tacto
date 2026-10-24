import { createFileRoute, Link } from "@tanstack/react-router";
import { Shell, MindsetBadge, StatusDot } from "@/components/Shell";
import { useCase, eur } from "@/lib/command";

export const Route = createFileRoute("/audit/$sessionId")({
  head: ({ params }) => ({
    meta: [
      { title: `Audit ${params.sessionId} · Hollerau Agentic Command` },
      { name: "description", content: "Turn-by-turn traceability log of every agent concession." },
      { property: "og:title", content: `Audit ${params.sessionId} · Hollerau Agentic Command` },
      { property: "og:description", content: "Turn-by-turn traceability log of every agent concession." },
    ],
  }),
  component: Audit,
});

function Audit() {
  const { sessionId } = Route.useParams();
  const { c, logs } = useCase(sessionId);
  const k = c.data;

  return (
    <Shell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="label-caps">C · Traceability audit · {sessionId}</div>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">{k?.supplier?.name ?? "…"}</h1>
          {k && <div className="mt-2 flex items-center gap-3 text-sm text-muted-foreground">{k.supplier?.segment} · {k.supplier?.country} <StatusDot s={k.status} /></div>}
        </div>
        <Link to="/briefing/$sessionId" params={{ sessionId }} className="bg-primary px-4 py-2 num text-xs font-semibold uppercase tracking-wider text-primary-foreground hover:opacity-90">
          D · Voice briefing →
        </Link>
      </div>

      {k && (
        <div className="mb-8 grid grid-cols-2 gap-px border border-border bg-border md:grid-cols-4">
          {[["C open", eur(k.c_open)], ["Current offer", eur(k.c_current_offer)], ["Best floor", eur(k.c_best_floor)], ["Score", Number(k.current_score).toFixed(3)]].map(([a, b]) => (
            <div key={a} className="bg-card p-4"><div className="label-caps">{a}</div><div className="mt-1 num text-2xl">{b}</div></div>
          ))}
        </div>
      )}

      <ol className="relative space-y-4 border-l border-border pl-6">
        {(logs.data ?? []).slice().reverse().map((l) => (
          <li key={l.id} className="relative">
            <span className="absolute -left-[29px] top-4 h-2.5 w-2.5 bg-primary" />
            <div className="panel p-5">
              <div className="flex flex-wrap items-center gap-4 border-b border-border pb-3">
                <span className="num text-sm font-semibold">TURN {l.turn_number}</span>
                <MindsetBadge m={l.supplier_mindset} />
                <span className="num text-xs text-muted-foreground">offered {eur(l.supplier_price_offered)}</span>
                <span className="num text-xs text-muted-foreground">local cost {eur(l.calculated_local_cost)}</span>
                <span className="num text-xs text-muted-foreground">velocity {Number(l.concession_velocity ?? 0).toFixed(4)}</span>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <Field k="Observed barrier" v={l.observed_barrier} />
                <Field k="Strategic intent" v={l.strategic_intent} />
                <Field k="Mathematical justification" v={l.mathematical_justification} mono />
              </div>
              {l.raw_email_sent && (
                <div className="mt-4 border-l-2 border-primary bg-muted/40 p-3 text-sm italic text-muted-foreground">{l.raw_email_sent}</div>
              )}
            </div>
          </li>
        ))}
        {logs.data?.length === 0 && <li className="text-muted-foreground">No turns logged yet.</li>}
      </ol>
    </Shell>
  );
}

function Field({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div>
      <div className="label-caps mb-1">{k}</div>
      <p className={`text-sm leading-relaxed ${mono ? "num text-primary" : ""}`}>{v}</p>
    </div>
  );
}
