import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { TermSheet } from "@/components/Telemetry";
import { MechanismStrip, NegotiationPath } from "@/components/NegotiationInsights";
import { supplierNames, useCase, useSuppliers } from "@/lib/command";
import { claimLabels, displayText, finalDealTerms, orderedTurns, parseMechanisms, percentScore, unitPrice } from "@/lib/telemetry";

export const Route = createFileRoute("/pitch/$sessionId")({
  head: ({ params }) => ({ meta: [
    { title: `Negotiation pitch ${params.sessionId} · Hollerau Agentic Command` },
    { name: "description", content: "Jury presentation of the negotiation path, evidence-backed moves and final deal terms." },
    { property: "og:title", content: `Negotiation pitch ${params.sessionId} · Hollerau Agentic Command` },
    { property: "og:description", content: "Jury presentation of the negotiation path, evidence-backed moves and final deal terms." },
    { property: "og:type", content: "website" }, { name: "twitter:card", content: "summary" },
  ] }),
  component: Pitch,
});

function Pitch() {
  const { sessionId } = Route.useParams();
  const { c, logs } = useCase(sessionId);
  const suppliers = useSuppliers();
  const negotiation = c.data;
  const turns = orderedTurns(logs.data ?? []);
  return <main className="pitch-page relative z-10 mx-auto max-w-[1400px] px-6 py-8">
    <div className="pitch-back mb-8"><Button asChild variant="ghost" size="sm"><Link to="/audit/$sessionId" params={{ sessionId }}>← back to audit</Link></Button></div>
    {c.isLoading ? <p>Loading…</p> : !negotiation ? <p className="text-muted-foreground">{c.isError ? "Negotiation data could not be loaded." : "-"}</p> : <>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-6 border-b border-border pb-6">
        <div className="min-w-0 max-w-4xl"><div className="label-caps mb-2">{sessionId} · {displayText(negotiation.case_type)}</div>
          <h1 className="break-words text-4xl font-semibold">{negotiation.title ?? negotiation.case_id}</h1>
          <p className="mt-3 break-words text-xl">{supplierNames(negotiation, suppliers.data)}</p>
          <p className="mt-2 text-lg text-muted-foreground">{displayText(negotiation.category_goal)}</p>
        </div>
        <div><div className="label-caps mb-2">Final score</div><div className="num text-5xl text-success">{percentScore(negotiation.score)}</div></div>
      </header>
      {logs.isError && <p role="alert" className="text-destructive">Negotiation turns could not be loaded.</p>}
      <NegotiationPath c={negotiation} logs={turns} suppliers={suppliers.data} />
      <section className="mb-8"><h2 className="mb-4 text-2xl font-semibold">Negotiation story</h2>
        <ol className="border-l border-border pl-5">{turns.map((l) => {
          const mechanisms = parseMechanisms(l.mathematical_justification ?? "");
          return <li key={l.id} className="pitch-turn border-b border-border py-4">
            <p className="break-words text-lg leading-relaxed"><span className="num">Turn {l.turn_number}</span> · {suppliers.data?.get(l.supplier_id)?.name ?? l.supplier_id} offered <span className="num">{unitPrice(l.supplier_terms?.unit_price)}</span> · we countered <span className="num">{unitPrice(l.proposed_terms?.unit_price)}</span> · {mechanisms.claimKind ? claimLabels[mechanisms.claimKind] : "-"}</p>
            <div className="mt-2"><MechanismStrip log={l} includeClaim={false} /></div>
          </li>;
        })}{!turns.length && <li className="py-4 text-muted-foreground">-</li>}</ol>
      </section>
      <section className="pitch-terms max-w-2xl border-t border-border pt-5"><h2 className="mb-4 text-2xl font-semibold">Final deal terms</h2><TermSheet label="Agreed terms" terms={finalDealTerms(negotiation, turns)} /></section>
    </>}
  </main>;
}