import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ClaimChips, CostBar, DecisionTag, ProtocolProfile, TermSheet, TelemetryCosts } from "@/components/Telemetry";
import type { CaseOverview, Supplier, Terms } from "@/integrations/hollerau/types";

const legacy: CaseOverview = {
  session_id: "test-only", case_id: "test", environment: "practice", wave: null, title: null,
  case_type: null, category_goal: null, supplier_ids: ["supplier"], status: "active", deal_supplier_id: null,
  c_open: 150000, c_alt: null, c_best: null, c_deal: null, score: null,
  started_at: "2026-10-24T18:00:00Z", ended_at: null, segment_protocol: null, culture_protocol: null,
  moves: 1, last_turn: 1, last_move_at: null, last_supplier_id: null, last_action: null,
  last_seconds_left: null, last_mindset: null, last_concession_velocity: null,
  last_c_supplier_offer: null, last_c_proposed: null, last_c_target: null,
  last_c_floor_est: null, last_decision_source: null,
};
const suppliers = new Map<string, Supplier>([["supplier", {
  id: "supplier", name: "Test supplier", country: "Germany", category: null, abc_class: null, synced_at: "2026-10-24T18:00:00Z",
}]]);

describe("Telemetry compatibility", () => {
  it("renders old rows with all nullable telemetry absent", () => {
    expect(() => renderToStaticMarkup(<><ProtocolProfile c={legacy} suppliers={suppliers} /><CostBar c={legacy} /><TermSheet label="Terms" terms={null} /><ClaimChips claims={null} /><DecisionTag source={null} latency={null} /><TelemetryCosts items={[["Target", null]]} /></>)).not.toThrow();
  });
  it("renders populated telemetry and structured index clauses", () => {
    const c: CaseOverview = { ...legacy, segment_protocol: "Leverage - Aggressive Protocol", culture_protocol: "Low-Context / Direct Specification", last_c_supplier_offer: 136500, last_c_target: 122000, last_c_floor_est: 120000, last_decision_source: "claude" };
    const terms: Terms = { unit_price: 123.45, ppm_commitment: 500, chargeback_eur_per_complaint: 75, index_clause: { series: "copper", material_share: 0.4, deadband_pct: 3, base_month: "2026-10" } };
    expect(() => renderToStaticMarkup(<><ProtocolProfile c={c} suppliers={suppliers} /><CostBar c={c} /><TermSheet label="Terms" terms={terms} /><ClaimChips claims={{ verified: 2, contradicted: 1, duplicate: 0, irrelevant: 0 }} /><DecisionTag source="claude" latency={6200} /><TelemetryCosts items={[["Target", 122000]]} /></>)).not.toThrow();
  });
});