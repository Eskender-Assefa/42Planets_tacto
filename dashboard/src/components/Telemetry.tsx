import type { CaseOverview, ClaimTally, DecisionSource, Supplier, Terms } from "@/integrations/hollerau/types";
import { eur } from "@/lib/command";
import { costPositions, countryFlag, decisionLabel, displayText, latencyLabel, protocolTone } from "@/lib/telemetry";

const tones = {
  success: "border-success/50 text-success bg-success/10",
  warning: "border-warning/50 text-warning bg-warning/10",
  info: "border-info/50 text-info bg-info/10",
  muted: "border-border text-muted-foreground bg-muted/40",
};

export function DecisionTag({ source, latency }: { source: DecisionSource | null | undefined; latency?: number | null }) {
  return <span className="inline-flex max-w-full items-center border border-border px-1.5 py-0.5 num text-[10px] text-muted-foreground">{decisionLabel(source)}{latency != null ? `, ${latencyLabel(latency)}` : ""}</span>;
}

export function ProtocolProfile({ c, suppliers }: { c: CaseOverview; suppliers: Map<string, Supplier> | undefined }) {
  const ids = c.last_supplier_id ? [c.last_supplier_id] : c.supplier_ids;
  const flags = [...new Set(ids.map((id) => countryFlag(suppliers?.get(id)?.country)))].join(" ") || "-";
  return <div className="min-w-0 space-y-2">
    <span className={`inline-block max-w-full break-words border px-2 py-1 text-xs ${tones[protocolTone(c.segment_protocol)]}`}>{displayText(c.segment_protocol)}</span>
    <div className="text-xs leading-relaxed text-muted-foreground"><div className="label-caps">Cultural profiler</div><span>{flags} {displayText(c.culture_protocol)}</span></div>
    <DecisionTag source={c.last_decision_source} />
  </div>;
}

export function CostBar({ c }: { c: CaseOverview }) {
  const markers = [
    { label: "Open · score 0", value: c.c_open, tone: "text-muted-foreground", dashed: false },
    { label: "Supplier now", value: c.last_c_supplier_offer, tone: "text-primary", dashed: false },
    { label: "Our target", value: c.last_c_target, tone: "text-success", dashed: false },
    { label: "Estimated floor", value: c.last_c_floor_est, tone: "text-info", dashed: true },
  ];
  const positions = costPositions(markers.map((m) => m.value));
  return <div>
    <div className="label-caps mb-2">Cost position · EUR</div>
    <div className="relative mx-1 h-14" role="img" aria-label={markers.map((m) => `${m.label}: ${eur(m.value)}`).join(", ")}>
      <div className="absolute inset-x-0 top-6 h-px bg-border" />
      {markers.map((m, i) => positions[i] == null ? null : <span key={m.label} title={`${m.label}: ${eur(m.value)}`} className={`absolute top-0 h-12 border-l-2 ${m.dashed ? "border-dashed" : "border-solid"} ${m.tone}`} style={{ left: `${positions[i]}%`, borderColor: "currentColor" }}><span className={`absolute -left-1 num text-[9px] ${i % 2 ? "top-8" : "top-0"}`}>{["O", "S", "T", "F"][i]}</span></span>)}
    </div>
    <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-[10px]">
      {markers.map((m) => <div key={m.label} className="min-w-0"><dt className={m.tone}>{m.label}</dt><dd className="num break-words">{eur(m.value)}</dd></div>)}
    </dl>
  </div>;
}

export function ClaimChips({ claims }: { claims: ClaimTally | null }) {
  if (!claims) return <span className="text-sm text-muted-foreground">-</span>;
  return <div className="flex flex-wrap gap-2">{(["verified", "contradicted", "duplicate", "irrelevant"] as const).map((key) => <span key={key} className={`border px-2 py-1 num text-[10px] ${key === "verified" ? tones.success : key === "contradicted" ? "border-destructive/50 text-destructive bg-destructive/10" : tones.muted}`}>{key} {claims[key] ?? "-"}</span>)}</div>;
}

const termLabels: [keyof Terms, string][] = [
  ["unit_price", "Unit price"], ["volume_per_year", "Volume / year"], ["contract_months", "Contract months"],
  ["payment_days", "Payment days"], ["lead_time_days", "Lead time days"], ["incoterm", "Incoterm"],
  ["index_clause", "Index clause"], ["tooling_eur", "Tooling"], ["effective_date", "Effective date"],
  ["ppm_commitment", "PPM commitment"], ["chargeback_eur_per_complaint", "Chargeback / complaint"],
];
function termValue(key: keyof Terms, terms: Terms) {
  const value = terms[key];
  if (value == null || value === "") return "-";
  if (typeof value === "object") return <dl className="space-y-1">{([["series", "Series"], ["material_share", "Material share"], ["deadband_pct", "Deadband %"], ["base_month", "Base month"]] as const).map(([k, label]) => <div key={k}><dt className="text-muted-foreground">{label}</dt><dd>{String(value[k] ?? "-")}</dd></div>)}</dl>;
  return ["unit_price", "tooling_eur", "chargeback_eur_per_complaint"].includes(key) && typeof value === "number" ? eur(value) : String(value);
}
export function TermSheet({ label, terms }: { label: string; terms: Terms | null }) {
  const rows = termLabels.filter(([key]) => terms?.[key] != null && terms[key] !== "");
  return <div><div className="label-caps mb-2">{label}</div>{!terms || !rows.length ? <p className="text-muted-foreground">-</p> : <dl className="text-xs">{rows.map(([key, label]) => <div key={key} className="grid grid-cols-2 gap-3 border-b border-border/60 py-2 last:border-0"><dt className="text-muted-foreground">{label}</dt><dd className="num min-w-0 break-words text-right">{termValue(key, terms)}</dd></div>)}</dl>}</div>;
}

export function TelemetryCosts({ items }: { items: [string, number | null | undefined][] }) {
  return <dl className="grid grid-cols-2 gap-3">{items.map(([label, value]) => <div key={label}><dt className="label-caps">{label}</dt><dd className="mt-1 num text-sm">{eur(value)}</dd></div>)}</dl>;
}
