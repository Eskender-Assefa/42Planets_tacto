import { describe, expect, it } from "vitest";
import { bestCaseScores, extractEvidence, finalDealTerms, leftOnTable, parseMechanisms, percentScore, summarizeMoves } from "@/lib/telemetry";
import type { AuditLog, CaseOverview } from "@/integrations/hollerau/types";

describe("Mechanism parsing", () => {
  it("reads an index claim", () => expect(parseMechanisms("C_open EUR 391,027.40 | ... | claim attached: index")).toEqual({ claimKind: "index", paced: [], swap: null }));
  it("reads paced moves and delivery claim", () => expect(parseMechanisms("... | paced to min C EUR 324,997.80: 5.30->5.45 | claim attached: delivery")).toEqual({ claimKind: "delivery", paced: [{ from: 5.30, to: 5.45 }], swap: null }));
  it("reads a trade", () => expect(parseMechanisms("... | swap offered: payment_days=14 for -5.0% (break-even -1.7%)")).toEqual({ claimKind: null, paced: [], swap: { field: "payment_days", value: "14", cutPct: 5 } }));
  it("returns empty mechanisms for missing traces", () => expect(parseMechanisms("-")).toEqual({ claimKind: null, paced: [], swap: null }));
  it("keeps multiple paced moves", () => expect(parseMechanisms("paced to min C EUR 1,000.00: 5.30->5.45, 6.10->6.20").paced).toEqual([{ from: 5.3, to: 5.45 }, { from: 6.1, to: 6.2 }]));
});

describe("Evidence extraction", () => {
  it("finds the first sentence and preserves dotted IDs", () => expect(extractEvidence("Hello. Our data idx:copper.2026 and fc:volume/07 show a fall. Another po:123 follows.")).toEqual({ sentence: "Our data idx:copper.2026 and fc:volume/07 show a fall.", ids: ["idx:copper.2026", "fc:volume/07"] }));
  it("returns null without evidence", () => { expect(extractEvidence(null)).toBeNull(); expect(extractEvidence("No data cited.")).toBeNull(); });
});

describe("Read-only insight calculations", () => {
  it("subtracts stored costs only for deals", () => { expect(leftOnTable({ status: "deal", c_deal: 131500, c_best: 122000 })).toBe(9500); expect(leftOnTable({ status: "active", c_deal: 131500, c_best: 122000 })).toBeNull(); expect(leftOnTable({ status: "deal", c_deal: null, c_best: 122000 })).toBeNull(); });
  it("formats stored scores as percentages", () => { expect(percentScore(0.525)).toBe("52.5 %"); expect(percentScore(null)).toBe("-"); });
  it("counts counters, paced turns and newest tally", () => {
    const logs = [{ id: 1, created_at: "2026-10-24", action: "send", proposed_terms: { unit_price: 5.45 }, mathematical_justification: "paced to min C EUR 100: 5.30->5.45, 6.10->6.20", claims: null }, { id: 2, created_at: "2026-10-25", action: "accept", proposed_terms: null, mathematical_justification: "-", claims: { verified: 4, irrelevant: 0, contradicted: 0, duplicate: 0 } }] as AuditLog[];
    expect(summarizeMoves(logs)).toEqual({ claims: logs[1].claims, claimTotal: 4, counters: 1, paced: 1 });
  });
  it("uses best score but newest audit session and sorts weakest first", () => {
    const cases = [{ case_id: "P07", case_type: "RFQ", session_id: "old", started_at: "2026-10-24", score: 0.8 }, { case_id: "P07", case_type: "RFQ", session_id: "new", started_at: "2026-10-25", score: 0.5 }, { case_id: "P01", case_type: "Price", session_id: "other", started_at: "2026-10-25", score: 0.2 }] as CaseOverview[];
    expect(bestCaseScores(cases)).toEqual([{ caseId: "P01", caseType: "Price", sessionId: "other", score: 0.2 }, { caseId: "P07", caseType: "RFQ", sessionId: "new", score: 0.8 }]);
  });
  it("uses accepted supplier terms and excludes other suppliers", () => {
    const c = { status: "deal", deal_supplier_id: "a" } as CaseOverview;
    const logs = [{ id: 1, turn_number: 1, created_at: "1", supplier_id: "a", action: "accept", supplier_terms: { unit_price: 5.45 } }, { id: 2, turn_number: 2, created_at: "2", supplier_id: "b", action: "send", proposed_terms: { unit_price: 9 } }] as AuditLog[];
    expect(finalDealTerms(c, logs)).toEqual({ unit_price: 5.45 });
  });
});