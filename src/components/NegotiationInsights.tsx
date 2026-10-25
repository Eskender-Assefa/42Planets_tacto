import { useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceDot, ReferenceLine, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Button } from "@/components/ui/button";
import { ClaimChips } from "@/components/Telemetry";
import type { AuditLog, CaseOverview, Supplier } from "@/integrations/hollerau/types";
import { eur } from "@/lib/command";
import { claimLabels, decisionLabel, evidenceIdPattern, extractEvidence, leftOnTable, orderedTurns, parseMechanisms, percentScore, shortEur } from "@/lib/telemetry";

export function MechanismStrip({ log, includeClaim = true }: { log: AuditLog; includeClaim?: boolean }) {
  const mechanisms = parseMechanisms(log.mathematical_justification ?? "");
  const chip = "inline-flex max-w-full break-words border border-border bg-muted/40 px-2 py-1 text-xs";
  return <div className="flex flex-wrap gap-2">
    {includeClaim && mechanisms.claimKind && <span className={`${chip} text-info`}>📎 {claimLabels[mechanisms.claimKind]}</span>}
    {mechanisms.paced.map((p, i) => <span key={i} className={`${chip} num text-warning`}>↗ Paced {p.from.toFixed(2)} → {p.to.toFixed(2)}</span>)}
    {mechanisms.swap && <span className={`${chip} text-success`}>Trade: {mechanisms.swap.field} {mechanisms.swap.value} for -{mechanisms.swap.cutPct}%</span>}
    {log.decision_source === "rule" && <span title={log.observed_barrier ?? "-"} className={chip}>Python rule</span>}
  </div>;
}

function EvidenceSentence({ sentence }: { sentence: string }) {
  const matches = [...sentence.matchAll(evidenceIdPattern())];
  let cursor = 0;
  return <>{matches.map((m, i) => {
    const index = m.index ?? 0;
    const before = sentence.slice(cursor, index);
    cursor = index + m[0].length;
    return <span key={i}>{before}<span className="num inline break-all border border-info/30 bg-info/10 px-1 text-xs text-info">{m[0]}</span></span>;
  })}{sentence.slice(cursor)}</>;
}

export function EvidenceCard({ log }: { log: AuditLog }) {
  const evidence = extractEvidence(log.message_body);
  if (!evidence) return null;
  return <div className="border-l-2 border-info bg-info/5 p-3">
    <div className="label-caps mb-2">Evidence</div>
    <p className="mb-3 whitespace-pre-wrap break-words text-sm leading-relaxed"><EvidenceSentence sentence={evidence.sentence} /></p>
    <ClaimChips claims={log.claims} />
  </div>;
}

export function HighlightedEmail({ body }: { body: string | null }) {
  const evidence = extractEvidence(body);
  if (!body) return <>-</>;
  if (!evidence) return <>{body}</>;
  const index = body.indexOf(evidence.sentence);
  return <>{body.slice(0, index)}<mark className="bg-info/15 text-foreground">{evidence.sentence}</mark>{body.slice(index + evidence.sentence.length)}</>;
}

const pathConfig = { c_supplier_offer: { label: "Supplier offer", color: "var(--primary)" }, c_proposed: { label: "Our counter", color: "var(--info)" } };

export function NegotiationPath({ c, logs, suppliers }: { c: CaseOverview; logs: AuditLog[]; suppliers: Map<string, Supplier> | undefined }) {
  const [selected, setSelected] = useState<string | null>(null);
  const ids = [...new Set([...c.supplier_ids, ...logs.map((l) => l.supplier_id)])];
  const active = selected && ids.includes(selected) ? selected : ids[0];
  const points = orderedTurns(logs.filter((l) => l.supplier_id === active));
  const last = points.at(-1);
  const deal = c.status === "deal" && c.c_deal != null && c.deal_supplier_id === active && last;
  return <section className="negotiation-path mb-8 min-w-0 border-y border-border py-5">
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-xl font-semibold">Negotiation path</h2>
      <div className="flex flex-wrap gap-2">{ids.map((id) => <Button key={id} size="sm" variant={active === id ? "secondary" : "ghost"} onClick={() => setSelected(id)}>{suppliers?.get(id)?.name ?? id}</Button>)}</div>
    </div>
    {points.length === 0 ? <p className="py-10 text-muted-foreground">-</p> : <ChartContainer config={pathConfig} className="h-[320px] w-full aspect-auto">
      <LineChart accessibilityLayer data={points} margin={{ top: 25, right: 22, bottom: 10, left: 12 }}>
        <CartesianGrid vertical={false} stroke="var(--border)" />
        <XAxis dataKey="turn_number" type="number" domain={["dataMin", "dataMax"]} allowDecimals={false} tickLine={false} axisLine={false} label={{ value: "Turn", position: "insideBottom", offset: -7, fill: "var(--muted-foreground)" }} />
        <YAxis tickFormatter={shortEur} width={78} domain={["auto", "auto"]} tickLine={false} axisLine={false} />
        <ChartTooltip content={<ChartTooltipContent labelFormatter={(_, payload) => `Turn ${payload[0]?.payload.turn_number ?? "-"} · ${decisionLabel(payload[0]?.payload.decision_source)}`} formatter={(value, name) => <div className="flex w-full justify-between gap-4"><span>{name === "c_supplier_offer" ? "Supplier offer" : "Our counter"}</span><span className="num">{eur(typeof value === "number" ? value : null)}</span></div>} />} />
        {([["Opening", c.c_open], ["Best possible", c.c_best], ["Alternative (no deal)", c.c_alt]] as const).map(([label, value], i) => value == null ? null : <ReferenceLine key={label} y={value} ifOverflow="extendDomain" stroke={i === 1 ? "var(--success)" : "var(--muted-foreground)"} strokeDasharray="4 4" label={{ value: label, position: "insideTopRight", fill: "var(--muted-foreground)", fontSize: 10 }} />)}
        <Line name="Supplier offer" dataKey="c_supplier_offer" stroke="var(--primary)" strokeWidth={2} dot={{ r: 4 }} isAnimationActive={false} connectNulls={false} />
        <Line name="Our counter" dataKey="c_proposed" stroke="var(--info)" strokeWidth={2} dot={{ r: 4 }} isAnimationActive={false} connectNulls={false} />
        {deal && <ReferenceDot x={last.turn_number} y={c.c_deal ?? undefined} r={7} fill="var(--success)" stroke="var(--background)" ifOverflow="extendDomain" label={{ value: "Deal", position: "top", fill: "var(--success)" }} />}
      </LineChart>
    </ChartContainer>}
    <div className="mt-3 flex flex-wrap gap-5 text-xs"><span className="text-primary">● Supplier offer</span><span className="text-info">● Our counter</span></div>
    {c.status === "deal" && <p className="mt-4 num text-sm">Captured {percentScore(c.score)} of the possible saving · {eur(leftOnTable(c))} left vs best possible</p>}
  </section>;
}