import { describe, expect, it } from "vitest";
import { buildBriefingScript, buildTurnSentence, freshNarration, spokenMoney, spokenUnitPrice } from "@/lib/briefing";
import type { AuditLog, CaseOverview } from "@/integrations/hollerau/types";

const c = { title: "Bundle the fastener kit", case_type: "bundling", status: "deal", supplier_ids: ["a"], deal_supplier_id: "a", score: 0.68, c_deal: 131500, c_best: 122000, last_turn: 4 } as CaseOverview;
const log = { id: 1, turn_number: 4, created_at: "2026-10-25T08:00:00Z", supplier_id: "a", action: "send", supplier_terms: { unit_price: 6 }, proposed_terms: { unit_price: 5.45, payment_days: 30, contract_months: 24 }, mathematical_justification: "paced to min C EUR 324,997.80: 5.30->5.45 | claim attached: delivery", message_body: "Our record sc:123 and idx:copper.2026 supports this.", claims: { verified: 2, irrelevant: 1, contradicted: 0, duplicate: 0 }, decision_source: "claude" } as AuditLog;
const name = () => "Nordmark";
describe("Browser briefing data rules", () => {
  it("speaks stored money in words-friendly form", () => { expect(spokenMoney(1522963)).toBe("1.52 million euros"); expect(spokenMoney(249273)).toBe("249 thousand euros"); expect(spokenUnitPrice(5.45)).toBe("5 euros 45"); });
  it("includes the deal outcome, stored score and claims", () => {
    const script = buildBriefingScript(c, [log], name, "summary");
    expect(script).toContain("We closed a deal with Nordmark after 4 rounds.");
    expect(script).toContain("We captured 68 percent of the possible saving, 10 thousand euros above the best possible cost.");
    expect(script).toContain("We argued with 3 data points, 2 of them verified by the supplier.");
  });
  it("speaks pacing without machine traces", () => {
    expect(buildBriefingScript(c, [log], name, "summary")).toContain("We moved every round and never took a concession back.");
    expect(buildTurnSentence(log, name)).toContain("We raised our own price from 5 euros 30 to 5 euros 45");
    for (const sentence of buildBriefingScript(c, [log], name, "full")) expect(sentence).not.toMatch(/\||idx:|sc:|EUR/);
  });
  it("uses accepted supplier terms and skips missing values", () => {
    const accepted = { ...log, id: 2, action: "accept", proposed_terms: null, supplier_terms: { unit_price: 5.5 }, claims: null } as AuditLog;
    expect(buildBriefingScript(c, [accepted], name, "summary")).toContain("Final terms: a unit price of 5 euros 50.");
    const empty = buildBriefingScript({ ...c, title: null, case_type: null, score: null, c_deal: null, c_best: null, supplier_ids: [], deal_supplier_id: null, last_turn: null }, [], () => "-", "summary");
    expect(empty).toEqual(["We closed a deal."]);
  });
  it("orders full turns and reports rule acceptance", () => {
    const last = { ...log, id: 2, turn_number: 5, created_at: "2026-10-25T08:01:00Z", decision_source: "rule", action: "accept", observed_barrier: "Supplier declared its final offer." } as AuditLog;
    const script = buildBriefingScript(c, [last, log], name, "full");
    expect(script.findIndex((s) => s.startsWith("Round 4."))).toBeLessThan(script.findIndex((s) => s.startsWith("Round 5.")));
    expect(script).toContain("When the supplier declared its final offer, we took it rather than risk a walk-away.");
  });
  it("drops live events older than 60 seconds", () => { const now = Date.parse("2026-10-25T08:01:00Z"); expect(freshNarration("2026-10-25T08:00:00Z", now)).toBe(true); expect(freshNarration("2026-10-25T07:59:59Z", now)).toBe(false); expect(freshNarration("-", now)).toBe(false); });
});