import type { AuditLog, CaseOverview, DecisionSource } from "@/integrations/hollerau/types";

export const decisionLabels: Record<DecisionSource, string> = {
  claude: "Claude", fallback: "Fallback", rule: "Rule", closing: "Time-cap close", naive: "Naive",
};

export const displayText = (value: string | null | undefined) => value?.trim() ? value : "-";
export const decisionLabel = (source: DecisionSource | null | undefined) => source ? decisionLabels[source] ?? "-" : "-";
export const latencyLabel = (ms: number | null | undefined) => ms == null ? "-" : `${(ms / 1000).toFixed(1)} s`;
export const velocityLabel = (velocity: number | null | undefined) => velocity == null ? "-" : `${velocity.toFixed(2)}% of C_open / round`;

export function protocolTone(protocol: string | null | undefined) {
  if (protocol?.startsWith("Leverage")) return "success";
  if (protocol?.startsWith("Strategic") || protocol?.startsWith("Bottleneck")) return "warning";
  if (protocol?.startsWith("Quality")) return "info";
  return "muted";
}

const countries: Record<string, string> = {
  germany: "DE", deutschland: "DE", austria: "AT", china: "CN", india: "IN", japan: "JP",
  france: "FR", italy: "IT", spain: "ES", poland: "PL", turkey: "TR", türkiye: "TR",
  "united kingdom": "GB", uk: "GB", "united states": "US", usa: "US", switzerland: "CH",
  netherlands: "NL", belgium: "BE", sweden: "SE", denmark: "DK", finland: "FI", norway: "NO",
  czechia: "CZ", "czech republic": "CZ", portugal: "PT", romania: "RO", hungary: "HU",
  vietnam: "VN", taiwan: "TW", "south korea": "KR", brazil: "BR", mexico: "MX", canada: "CA",
};
export function countryFlag(country: string | null | undefined): string {
  if (!country?.trim()) return "-";
  const value = country.trim();
  const code = countries[value.toLowerCase()] ?? (/^[A-Za-z]{2}$/.test(value) ? value.toUpperCase() : null);
  return code ? [...code].map((c) => String.fromCodePoint(127397 + c.charCodeAt(0))).join("") : value;
}

/** Visual coordinates only: descending stored euro values, never a cost or score calculation. */
export function costPositions(values: (number | null | undefined)[]): (number | null)[] {
  const finite = values.filter((v): v is number => v != null && Number.isFinite(v));
  if (!finite.length) return values.map(() => null);
  const high = Math.max(...finite);
  const low = Math.min(...finite);
  return values.map((v) => v == null || !Number.isFinite(v) ? null : high === low ? 0 : (high - v) / (high - low) * 100);
}

export const claimLabels: Record<string, string> = {
  index: "Index fall", notice: "Notice period", should_cost: "Cost estimate", volume: "Volume forecast",
  delivery: "Delivery record", quality: "Defect rate", history: "Order history", rival_offer: "Rival's live offer", news: "Supplier news",
};

export function parseMechanisms(justification: string): { claimKind: string | null; paced: { from: number; to: number }[]; swap: { field: string; value: string; cutPct: number } | null } {
  const result: ReturnType<typeof parseMechanisms> = { claimKind: null, paced: [], swap: null };
  for (const tag of justification.split(" | ")) {
    const claim = tag.trim().match(/^claim attached: (\w+)$/);
    if (claim && claimLabels[claim[1]]) result.claimKind = claim[1];
    if (tag.trim().startsWith("paced to min C EUR ")) {
      const pairs = tag.slice(tag.indexOf(":") + 1).matchAll(/(-?\d+(?:\.\d+)?)\s*->\s*(-?\d+(?:\.\d+)?)/g);
      for (const pair of pairs) result.paced.push({ from: Number(pair[1]), to: Number(pair[2]) });
    }
    const swap = tag.trim().match(/^swap offered: (\w+)=(.+?) for -(\d+(?:\.\d+)?)% \(break-even -\d+(?:\.\d+)?%\)$/);
    if (swap) result.swap = { field: swap[1], value: swap[2], cutPct: Number(swap[3]) };
  }
  return result;
}

export const evidenceIdPattern = () => /\b(?:idx|quote|offer|sc|qn|po|cost|fc|news|doc|ctr):[\w.:@#/-]*\w/g;

export function extractEvidence(body: string | null): { sentence: string; ids: string[] } | null {
  if (!body) return null;
  const first = evidenceIdPattern().exec(body);
  if (!first) return null;
  const boundaries = [...body.matchAll(/[.!?](?=\s|$)/g)].map((m) => m.index ?? 0);
  const start = (boundaries.filter((i) => i < first.index).at(-1) ?? -1) + 1;
  const end = boundaries.find((i) => i >= first.index + first[0].length) ?? body.length;
  const sentence = body.slice(start, Math.min(end + 1, body.length)).trim();
  return { sentence, ids: sentence.match(evidenceIdPattern()) ?? [] };
}

export const shortEur = (value: number | null | undefined) => value == null ? "-" : new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR", notation: "compact", maximumFractionDigits: 2 }).format(value);
export const unitPrice = (value: number | null | undefined) => value == null ? "-" : value.toFixed(2);
export const leftOnTable = (c: Pick<CaseOverview, "status" | "c_deal" | "c_best">) => c.status === "deal" && c.c_deal != null && c.c_best != null ? c.c_deal - c.c_best : null;
export const percentScore = (value: number | null | undefined) => value == null ? "-" : `${(value * 100).toFixed(1)} %`;
export const orderedTurns = (logs: AuditLog[]) => logs.slice().sort((a, b) => a.turn_number - b.turn_number || a.created_at.localeCompare(b.created_at) || a.id - b.id);

export function summarizeMoves(logs: AuditLog[]) {
  const ordered = logs.slice().sort((a, b) => a.created_at.localeCompare(b.created_at) || a.id - b.id);
  const claims = ordered.at(-1)?.claims ?? null;
  const counters = logs.filter((l) => l.action === "send" && l.proposed_terms != null);
  return { claims, claimTotal: claims ? claims.verified + claims.irrelevant + claims.contradicted + claims.duplicate : null,
    counters: counters.length, paced: counters.filter((l) => parseMechanisms(l.mathematical_justification ?? "").paced.length > 0).length };
}

export function bestCaseScores(cases: CaseOverview[]) {
  const groups = new Map<string, CaseOverview[]>();
  for (const c of cases) groups.set(c.case_id, [...(groups.get(c.case_id) ?? []), c]);
  return [...groups.values()].map((rows) => {
    const newest = rows.slice().sort((a, b) => b.started_at.localeCompare(a.started_at))[0];
    const scores = rows.map((r) => r.score).filter((s): s is number => s != null);
    return { caseId: newest.case_id, caseType: newest.case_type ?? "-", sessionId: newest.session_id, score: scores.length ? Math.max(...scores) : null };
  }).sort((a, b) => (a.score ?? Infinity) - (b.score ?? Infinity) || a.caseId.localeCompare(b.caseId));
}

export function finalDealTerms(c: CaseOverview, logs: AuditLog[]) {
  if (c.status !== "deal") return null;
  const turns = orderedTurns(logs.filter((l) => !c.deal_supplier_id || l.supplier_id === c.deal_supplier_id));
  const last = turns.at(-1);
  return last?.action === "accept" ? last.supplier_terms : last?.proposed_terms ?? null;
}