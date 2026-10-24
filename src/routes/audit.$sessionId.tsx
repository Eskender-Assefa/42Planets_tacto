import { createFileRoute, Link } from "@tanstack/react-router";
import { Shell, MindsetBadge, StatusDot } from "@/components/Shell";
import { useCase, useSuppliers, supplierNames, eur, scoreLabel } from "@/lib/command";
import type { Terms } from "@/integrations/hollerau/types";

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
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">{k ? (k.title ?? k.case_id) : "…"}</h1>
          {k && (
            <div className="mt-2 flex items-center gap-3 text-sm text-muted-foreground">
              {supplierNames(k, suppliers.data)} · {k.category_goal ?? "—"} <StatusDot s={k.status} />
            </div>
          )}
        </div>
        <Link to="/briefing/$sessionId" params={{ sessionId }} className="bg-primary px-4 py-2 num text-xs font-semibold uppercase tracking-wider text-primary-foreground hover:opacity-90">
          D · Voice briefing →
        </Link>
      </div>

      {k && (
        <div className="mb-8 grid grid-cols-2 gap-px border border-border bg-border md:grid-cols-4">
          {[["C open", eur(k.c_open)], ["Last offer", eur(k.last_c_supplier_offer)], ["C best", eur(k.c_best)], ["Score", scoreLabel(k.score)]].map(([a, b]) => (
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
                <span className="num text-xs uppercase tracking-wider text-muted-foreground">{suppliers.data?.get(l.supplier_id)?.name ?? l.supplier_id}</span>
                <span className="num text-xs uppercase tracking-wider text-primary">{l.action.replace("_", " ")}</span>
                <MindsetBadge m={l.supplier_mindset} />
                <span className="num text-xs text-muted-foreground">supplier offer {eur(l.c_supplier_offer)}</span>
                <span className="num text-xs text-muted-foreground">proposed {eur(l.c_proposed)}</span>
                <span className="num text-xs text-muted-foreground">velocity {l.concession_velocity?.toFixed(4) ?? "—"}</span>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <Field k="Observed barrier" v={l.observed_barrier} />
                <Field k="Strategic intent" v={l.strategic_intent} />
                <Field k="Mathematical justification" v={l.mathematical_justification} mono />
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <TermSheet k="Supplier terms" t={l.supplier_terms} />
                <TermSheet k="Proposed terms" t={l.proposed_terms} />
              </div>
              {(l.message_subject || l.message_body) && (
                <div className="mt-4 border-l-2 border-primary bg-muted/40 p-3 text-sm italic text-muted-foreground">
                  {l.message_subject && <div className="mb-1 not-italic num text-xs uppercase tracking-wider text-foreground">{l.message_subject}</div>}
                  {l.message_body}
                </div>
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

const TERM_LABELS: [keyof Terms, string][] = [
  ["unit_price", "Unit price"],
  ["volume_per_year", "Volume / year"],
  ["contract_months", "Contract months"],
  ["payment_days", "Payment days"],
  ["lead_time_days", "Lead time days"],
  ["incoterm", "Incoterm"],
  ["index_clause", "Index clause"],
  ["tooling_eur", "Tooling"],
  ["effective_date", "Effective date"],
];

function TermSheet({ k, t }: { k: string; t: Terms | null }) {
  const rows = TERM_LABELS.filter(([key]) => t?.[key] != null);
  return (
    <div>
      <div className="label-caps mb-1">{k}</div>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">—</p>
      ) : (
        <dl className="border border-border text-xs">
          {rows.map(([key, label]) => (
            <div key={key} className="flex justify-between gap-4 border-b border-border/60 px-3 py-1.5 last:border-b-0">
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="num">{key === "unit_price" || key === "tooling_eur" ? eur(t?.[key] as number) : String(t?.[key])}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
