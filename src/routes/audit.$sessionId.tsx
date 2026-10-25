import { createFileRoute, Link } from "@tanstack/react-router";
import { Shell, MindsetBadge, StatusDot } from "@/components/Shell";
import { useCase, useSuppliers, supplierNames, eur, scoreLabel } from "@/lib/command";
import { ClaimChips, DecisionTag, TelemetryCosts, TermSheet } from "@/components/Telemetry";
import { displayText, latencyLabel, velocityLabel } from "@/lib/telemetry";
import { Button } from "@/components/ui/button";
import { EvidenceCard, HighlightedEmail, MechanismStrip, NegotiationPath } from "@/components/NegotiationInsights";

export const Route = createFileRoute("/audit/$sessionId")({
  head: ({ params }) => ({
    meta: [
      { title: `Audit ${params.sessionId} · Hollerau Agentic Command` },
      { name: "description", content: "Turn-by-turn traceability log of every agent concession." },
      { property: "og:title", content: `Audit ${params.sessionId} · Hollerau Agentic Command` },
      { property: "og:description", content: "Turn-by-turn traceability log of every agent concession." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Audit,
});

function Audit() {
  const { sessionId } = Route.useParams();
  const { c, logs } = useCase(sessionId);
  const suppliers = useSuppliers();
  const k = c.data;

  return (
    <Shell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="label-caps">C · Traceability audit · {sessionId}</div>
          <h1 className="mt-1 break-words text-3xl font-semibold">{k ? (k.title ?? k.case_id) : "-"}</h1>
          {k && (
            <div className="mt-2 flex items-center gap-3 text-sm text-muted-foreground">
              {supplierNames(k, suppliers.data)} · {k.category_goal ?? "-"} <StatusDot s={k.status} />
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-2"><Button asChild variant="outline"><Link to="/pitch/$sessionId" params={{ sessionId }} className="num text-xs">Pitch view →</Link></Button><Button asChild><Link to="/briefing/$sessionId" params={{ sessionId }} className="num text-xs">D · Voice briefing →</Link></Button></div>
      </div>

      {k && (
        <div className="mb-8 grid grid-cols-2 gap-px border border-border bg-border md:grid-cols-4">
          {[["C open", eur(k.c_open)], ["Last offer", eur(k.last_c_supplier_offer)], ["C best", eur(k.c_best)], ["Score", scoreLabel(k.score)]].map(([a, b]) => (
            <div key={a} className="bg-card p-4"><div className="label-caps">{a}</div><div className="mt-1 num text-2xl">{b}</div></div>
          ))}
        </div>
      )}

      {k && <NegotiationPath c={k} logs={logs.data ?? []} suppliers={suppliers.data} />}
      {(c.isError || logs.isError) && <p role="alert" className="mb-4 text-destructive">Negotiation data could not be loaded.</p>}
      <ol className="relative space-y-4 border-l border-border pl-6">
        {(logs.data ?? []).slice().reverse().map((l) => (
          <li key={l.id} className="relative">
            <span className="absolute -left-[29px] top-4 h-2.5 w-2.5 bg-primary" />
            <div className="panel p-5">
              <div className="flex flex-wrap items-center gap-4 border-b border-border pb-3">
                <span className="num text-sm font-semibold">TURN {l.turn_number}</span>
                <span className="num text-xs uppercase tracking-wider text-muted-foreground">{suppliers.data?.get(l.supplier_id)?.name ?? l.supplier_id}</span>
                <span className="num text-xs text-muted-foreground">{l.created_at ? new Date(l.created_at).toLocaleString() : "-"}</span>
              </div>
              <div className="mt-5 grid gap-6 xl:grid-cols-3">
                <section className="min-w-0 space-y-4 xl:border-r xl:border-border xl:pr-6">
                  <h2 className="flex items-center gap-2 text-sm font-semibold"><span aria-hidden="true">🔍</span> 1 · Ingesting</h2>
                  <TermSheet label="Supplier terms" terms={l.supplier_terms} />
                  <TelemetryCosts items={[["Supplier offer", l.c_supplier_offer], ...(l.penalty_at_offer != null ? [["Supplier-health penalty", l.penalty_at_offer] as [string, number]] : [])]} />
                  <div><div className="label-caps mb-1">Supplier mindset</div><MindsetBadge m={l.supplier_mindset} /></div>
                  <div><div className="label-caps mb-1">Concession velocity</div><p className="num text-xs">{velocityLabel(l.concession_velocity)}</p></div>
                </section>
                <section className="min-w-0 space-y-4 xl:border-r xl:border-border xl:pr-6">
                  <h2 className="flex items-center gap-2 text-sm font-semibold"><span aria-hidden="true">🧮</span> 2 · Calculating</h2>
                  <TelemetryCosts items={[["Proposed cost", l.c_proposed], ["Target cost", l.c_target], ["Estimated floor", l.c_floor_est]]} />
                  <Field k="Mathematical justification" v={l.mathematical_justification} mono />
                </section>
                <section className="min-w-0 space-y-4">
                  <h2 className="flex items-center gap-2 text-sm font-semibold"><span aria-hidden="true">💡</span> 3 · Decision</h2>
                  <div className="flex flex-wrap items-center gap-2"><span className="num text-xs uppercase text-primary">{l.action?.replace("_", " ") ?? "-"}</span><DecisionTag source={l.decision_source} latency={l.llm_latency_ms} /></div>
                  {l.llm_latency_ms == null && <div className="text-xs text-muted-foreground">LLM latency: {latencyLabel(l.llm_latency_ms)}</div>}
                  <TermSheet label="Proposed terms" terms={l.proposed_terms} />
                   <MechanismStrip log={l} />
                   <EvidenceCard log={l} />
                  <Field k="Strategic intent" v={l.strategic_intent} />
                  <Field k="Observed barrier" v={l.observed_barrier} />
                  <div><div className="label-caps mb-2">Claim verdicts</div><ClaimChips claims={l.claims} /></div>
                  <div className="border-l-2 border-primary bg-muted/40 p-3 text-sm text-muted-foreground">
                    <div className="label-caps mb-2">E-mail</div>
                    <div className="mb-2 break-words font-medium text-foreground">{displayText(l.message_subject)}</div>
                    <p className="whitespace-pre-wrap break-words leading-relaxed"><HighlightedEmail body={l.message_body} /></p>
                  </div>
                </section>
              </div>
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
      <p className={`whitespace-pre-wrap break-words text-sm leading-relaxed ${mono ? "num text-primary" : ""}`}>{displayText(v)}</p>
    </div>
  );
}

