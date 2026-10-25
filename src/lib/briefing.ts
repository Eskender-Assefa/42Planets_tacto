import type { AuditLog, CaseOverview, Terms } from "@/integrations/hollerau/types";
import { extractEvidence, evidenceIdPattern, finalDealTerms, orderedTurns, parseMechanisms, summarizeMoves } from "@/lib/telemetry";

export type BriefingMode = "summary" | "full";
const clean = (value: string | null | undefined) => (value ?? "").replace(evidenceIdPattern(), "").replace(/\bEUR\b/g, "euros").replace(/[|_<>€]/g, " ").replace(/\s+/g, " ").trim();
const number = (n: number) => Number(n.toFixed(2)).toString();
export function spokenMoney(value: number): string {
  const sign = value < 0 ? "minus " : "";
  const n = Math.abs(value);
  return sign + (n >= 1e6 ? `${number(n / 1e6)} million euros` : n >= 1000 ? `${Math.round(n / 1000)} thousand euros` : `${number(n)} euros`);
}
export function spokenUnitPrice(value: number): string {
  const cents = Math.round(Math.abs(value) * 100);
  return `${value < 0 ? "minus " : ""}${Math.floor(cents / 100)} euros${cents % 100 ? ` ${cents % 100}` : ""}`;
}
const list = (items: string[]) => items.length < 2 ? items.join("") : `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;
const argumentsByKind: Record<string, string> = { index: "an index fall", notice: "the notice period", should_cost: "a cost estimate", volume: "a volume forecast", delivery: "the supplier's delivery record", quality: "the defect rate", history: "the order history", rival_offer: "a rival's live offer", news: "supplier news" };
const types: Record<string, string> = { price: "price increase", price_increase: "price increase", renewal: "renewal", rfq: "request for quotation", request_for_quotation: "request for quotation", bundling: "bundling", bundle: "bundling", raw_material: "raw material", capacity: "capacity", quality: "quality" };

export function buildTurnSentence(log: AuditLog, supplierName: (id: string) => string): string {
  const parts = [`Round ${log.turn_number}.`];
  const name = clean(supplierName(log.supplier_id));
  if (log.supplier_terms?.unit_price != null) parts.push(`${name && name !== "-" && name !== log.supplier_id ? name : "The supplier"} offered ${spokenUnitPrice(log.supplier_terms.unit_price)}.`);
  const mechanism = parseMechanisms(log.mathematical_justification ?? "");
  // Read the stored evidence, but never speak its machine identifiers.
  const evidence = extractEvidence(log.message_body);
  const claim = mechanism.claimKind ? argumentsByKind[mechanism.claimKind] : null;
  if (log.action === "send" && log.proposed_terms?.unit_price != null) parts.push(`We countered at ${spokenUnitPrice(log.proposed_terms.unit_price)}${claim ? `, citing ${claim}` : evidence ? ", citing our supporting data" : ""}.`);
  for (const paced of mechanism.paced) parts.push(`We raised our own price from ${spokenUnitPrice(paced.from)} to ${spokenUnitPrice(paced.to)} to keep the negotiation moving.`);
  if (log.action === "accept") parts.push("We accepted.");
  if (log.action === "walk_away") parts.push("We walked away.");
  return parts.join(" ");
}

function termsSentence(terms: Terms | null): string | null {
  if (!terms) return null;
  const fields: string[] = [];
  if (terms.unit_price != null) fields.push(`a unit price of ${spokenUnitPrice(terms.unit_price)}`);
  if (terms.payment_days != null) fields.push(`payment in ${terms.payment_days} days`);
  if (terms.contract_months != null) fields.push(`a ${terms.contract_months} month contract`);
  const clause = terms.index_clause;
  if (clause?.series) fields.push(`a ${clean(clause.series)} index clause${clause.deadband_pct != null ? ` with ${number(clause.deadband_pct)} percent deadband` : ""}`);
  return fields.length ? `Final terms: ${list(fields)}.` : null;
}

export function buildBriefingScript(c: CaseOverview, logs: AuditLog[], supplierName: (id: string) => string, mode: BriefingMode): string[] {
  const turns = orderedTurns(logs);
  const sentences: string[] = [];
  const names = c.supplier_ids.map((id) => { const name = clean(supplierName(id)); return name !== id && name !== "-" ? name : ""; }).filter(Boolean);
  const title = clean(c.title);
  if (title || names.length) sentences.push(`Briefing${title ? ` for ${title}` : ""}${names.length ? `, with ${list(names)}` : ""}.`);
  const type = c.case_type ? types[c.case_type.toLowerCase().replace(/[ -]/g, "_")] : null;
  if (type) sentences.push(`This is a ${type} negotiation.`);
  const rounds = c.last_turn ?? turns.at(-1)?.turn_number;
  const winner = c.deal_supplier_id ? clean(supplierName(c.deal_supplier_id)) : "";
  if (c.status === "deal") sentences.push(`We closed a deal${winner && winner !== "-" && winner !== c.deal_supplier_id ? ` with ${winner}` : ""}${rounds != null ? ` after ${rounds} rounds` : ""}.`);
  if (c.status === "walked_away") sentences.push("We walked away because the alternative was cheaper.");
  if (c.status === "no_deal") sentences.push("The case ended without a deal.");
  if (c.status === "active") sentences.push(`The negotiation is still running${rounds != null ? `, round ${rounds}` : ""}.`);
  if (mode === "full") sentences.push(...turns.map((l) => buildTurnSentence(l, supplierName)));
  if (c.status === "deal") {
    const gap = c.c_deal != null && c.c_best != null ? c.c_deal - c.c_best : null;
    if (c.score != null) sentences.push(`We captured ${number(c.score * 100)} percent of the possible saving${gap != null ? `, ${spokenMoney(gap)} above the best possible cost` : ""}.`);
    else if (gap != null) sentences.push(`The deal was ${spokenMoney(gap)} above the best possible cost.`);
  }
  const { claims, claimTotal } = summarizeMoves(turns);
  if (claims && claimTotal != null) sentences.push(`We argued with ${claimTotal} data points, ${claims.verified} of them verified by the supplier.`);
  const kinds = [...new Set(turns.map((l) => parseMechanisms(l.mathematical_justification ?? "").claimKind).filter((kind): kind is string => kind != null))];
  if (kinds.length) sentences.push(`Our arguments: ${list(kinds.map((kind) => argumentsByKind[kind] ?? "supporting data"))}.`);
  if (turns.some((l) => parseMechanisms(l.mathematical_justification ?? "").paced.length)) sentences.push("We moved every round and never took a concession back.");
  if (turns.some((l) => l.decision_source === "rule" && l.observed_barrier === "Supplier declared its final offer.")) sentences.push("When the supplier declared its final offer, we took it rather than risk a walk-away.");
  const terms = c.status === "deal" ? finalDealTerms(c, turns) : turns.slice().reverse().find((l) => l.proposed_terms)?.proposed_terms ?? null;
  const final = termsSentence(terms);
  if (final) sentences.push(final);
  return sentences;
}

export const freshNarration = (createdAt: string, now = Date.now()) => Number.isFinite(Date.parse(createdAt)) && now - Date.parse(createdAt) <= 60_000;
export function buildLiveSentence(c: CaseOverview, log: AuditLog | null, supplierName: (id: string) => string): string {
  const title = clean(c.title) || "Negotiation";
  if (c.status === "deal") return `${title}: deal${log?.supplier_terms?.unit_price != null ? ` at ${spokenUnitPrice(log.supplier_terms.unit_price)}` : ""}${c.score != null ? `, ${number(c.score * 100)} percent` : ""}.`;
  if (!log) return `${title}: ${c.status === "walked_away" ? "we walked away" : "the case ended without a deal"}.`;
  const name = clean(supplierName(log.supplier_id));
  const parts = [log.supplier_terms?.unit_price != null ? `${name && name !== log.supplier_id && name !== "-" ? name : "the supplier"} offered ${spokenUnitPrice(log.supplier_terms.unit_price)}` : "", log.action === "send" && log.proposed_terms?.unit_price != null ? `we countered ${spokenUnitPrice(log.proposed_terms.unit_price)}` : log.action === "accept" ? "we accepted" : log.action === "walk_away" ? "we walked away" : ""].filter(Boolean);
  return parts.length ? `${title}: ${parts.join(", ")}.` : "";
}