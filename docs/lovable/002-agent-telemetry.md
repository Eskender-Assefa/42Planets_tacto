# Lovable prompt 002 - agent telemetry: protocols, envelope, decision source

Paste everything below the line into Lovable after running `db/migrations/003_agent_telemetry.sql`.

---

The Supabase schema gained agent telemetry. Update the dashboard to show it. Read-only as before; no
mock data; empty/NULL values render as "-".

## 1. Replace the types contract
Replace `src/integrations/hollerau/types.ts` with EXACTLY this content (byte for byte; our backend
diffs it against its own copy):

```ts
// Row shapes of the Supabase schema in db/migrations/001_init.sql.
// Keep in sync with the migration and with starter-kit/hollerau/types.py.
// NUMERIC columns arrive from PostgREST as numbers; TIMESTAMPTZ as ISO-8601 strings.

export type Environment = "sim" | "practice" | "final";

export type CaseStatus = "active" | "deal" | "walked_away" | "no_deal" | "error";

export type MoveAction = "send" | "accept" | "walk_away";

/** Who made a move: Claude, a deterministic fallback, a Python rule, the time-cap close, the naive agent. */
export type DecisionSource = "claude" | "fallback" | "rule" | "closing" | "naive";

/** The arena's verdicts on the data IDs we cited (only the first 3 per message are checked). */
export interface ClaimTally {
  verified: number;
  irrelevant: number;
  contradicted: number;
  duplicate: number;
}

/** An index-linked price clause (option values from the case's term_options). */
export interface IndexClause {
  series: string;
  material_share: number;
  deadband_pct: number;
  base_month: string;
}

/** A term sheet as the arena sends it; every field is optional because sheets can be partial. */
export interface Terms {
  unit_price?: number | null;
  volume_per_year?: number | null;
  contract_months?: number | null;
  payment_days?: number | null;
  lead_time_days?: number | null;
  incoterm?: string | null;
  index_clause?: IndexClause | null;
  tooling_eur?: number | null;
  effective_date?: string | null;
  ppm_commitment?: number | null;
  chargeback_eur_per_complaint?: number | null;
}

export interface Supplier {
  id: string;
  name: string;
  country: string | null;
  category: string | null;
  abc_class: string | null;
  synced_at: string;
}

export interface Case {
  session_id: string;
  case_id: string;
  environment: Environment;
  wave: number | null;
  title: string | null;
  case_type: string | null;
  category_goal: string | null;
  supplier_ids: string[];
  status: CaseStatus;
  deal_supplier_id: string | null;
  c_open: number | null;
  c_alt: number | null;
  c_best: number | null;
  c_deal: number | null;
  score: number | null;
  started_at: string;
  ended_at: string | null;
  segment_protocol: string | null;
  culture_protocol: string | null;
}

export interface AuditLog {
  id: number;
  session_id: string;
  supplier_id: string;
  turn_number: number;
  created_at: string;
  seconds_left: number | null;
  action: MoveAction;
  supplier_terms: Terms | null;
  proposed_terms: Terms | null;
  c_supplier_offer: number | null;
  c_proposed: number | null;
  concession_velocity: number | null;
  supplier_mindset: string | null;
  observed_barrier: string;
  strategic_intent: string;
  mathematical_justification: string;
  message_subject: string | null;
  message_body: string | null;
  c_target: number | null;
  c_floor_est: number | null;
  penalty_at_offer: number | null;
  claims: ClaimTally | null;
  decision_source: DecisionSource | null;
  llm_latency_ms: number | null;
}

/** One row per case with the newest audit row's live state (view `case_overview`). */
export interface CaseOverview extends Case {
  moves: number;
  last_turn: number | null;
  last_move_at: string | null;
  last_supplier_id: string | null;
  last_action: MoveAction | null;
  last_seconds_left: number | null;
  last_mindset: string | null;
  last_concession_velocity: number | null;
  last_c_supplier_offer: number | null;
  last_c_proposed: number | null;
  last_c_target: number | null;
  last_c_floor_est: number | null;
  last_decision_source: DecisionSource | null;
}

export interface WaveScore {
  environment: Environment;
  wave: number | null;
  cases_played: number;
  deals: number;
  avg_score: number | null;
  total_score: number;
}
```

## 2. New columns
- `cases.segment_protocol` (e.g. "Leverage - Aggressive Protocol", "Strategic - Safeguard Protocol",
  "Bottleneck - Protection Protocol", "Quality Escalation Protocol", "Routine - Efficiency Protocol")
- `cases.culture_protocol` (e.g. "Low-Context / Direct Specification", "High-Context /
  Relationship-Preserving")
- `audit_logs`: `c_target` (C of the sheet the agent aimed for), `c_floor_est` (C at the supplier's
  estimated floor - our live stand-in for the hidden best), `penalty_at_offer` (estimated
  supplier-health charge inside the supplier's offer), `claims` (ClaimTally of the arena's verdicts
  on cited data), `decision_source` ("claude" | "fallback" | "rule" | "closing" | "naive"),
  `llm_latency_ms`
- `case_overview` adds `last_c_target`, `last_c_floor_est`, `last_decision_source`

## 3. UI changes
- **Wave monitor cards**: a protocol badge from `segment_protocol` - Leverage = green, Strategic /
  Bottleneck = amber, Quality = blue, Routine = grey; under it a small "Cultural profiler" line:
  supplier country flag + `culture_protocol`. Show `last_decision_source` as a tiny tag
  (Claude / Fallback / Rule / Time-cap close / Naive).
- **Card cost bar**: three markers on one horizontal euro scale - `c_open` (left, score 0),
  `last_c_supplier_offer` (supplier now), `last_c_target` (our target); plus `last_c_floor_est` as
  a dashed marker. Pure positioning of stored values - no score or savings maths.
- **Audit view (`/audit/$sessionId`)**: render each audit row as three steps:
  1. 🔍 Ingesting - `supplier_terms` table, `c_supplier_offer`, `supplier_mindset`,
     `concession_velocity` (% of C_open per round), `penalty_at_offer` if not null
  2. 🧮 Calculating - `c_proposed`, `c_target`, `c_floor_est`, and `mathematical_justification`
     verbatim (it is written by the cost engine)
  3. 💡 Decision - `action`, `proposed_terms`, `strategic_intent`, `observed_barrier`,
     `decision_source` tag, `llm_latency_ms` ("Claude, 6.2 s"), claim verdict chips from `claims`
     (verified green, contradicted red, duplicate/irrelevant grey); then the e-mail
     (`message_subject`, `message_body`)
- **Scoreboard**: unchanged.

## 4. Done when
Build, `vitest` and `tsc --noEmit` pass; every view renders with the new columns NULL (old rows)
and filled (new rows).
