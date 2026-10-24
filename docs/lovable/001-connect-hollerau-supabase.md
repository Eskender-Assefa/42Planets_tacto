# Lovable prompt 001 - connect the dashboard to the Hollerau Supabase project

Paste everything below the line into Lovable. Replace `<ANON_KEY>` with the project's anon /
publishable key (Supabase → Project Settings → API Keys). It is a public, read-only key; never
give Lovable the service-role / secret key.

---

Switch this dashboard's data source to our own Supabase project and its schema. The Python
negotiation runner already writes there; the dashboard only reads.

## 1. Data source
- Create `src/integrations/hollerau/config.ts` exporting:
  - `HOLLERAU_SUPABASE_URL = "https://uewawemvntlaqarnuvom.supabase.co"`
  - `HOLLERAU_SUPABASE_ANON_KEY = "<ANON_KEY>"` (public read-only key; safe in the browser)
- Create `src/integrations/hollerau/client.ts`: a supabase-js client built from that config, typed
  with the types in step 2. Do not use or modify `src/integrations/supabase/*` (that is Lovable
  Cloud, auto-generated) for dashboard data any more.
- Point every query and realtime subscription in the app (currently in `src/lib/command.ts`) at the
  new client. Read-only: never insert, update or delete from the dashboard. No login required.
- Remove the old demo tables' data usage. Do not add mock, sample or hardcoded rows anywhere in
  the code; when tables are empty, show clean empty states ("No cases yet - start the runner").

## 2. Types contract
Create `src/integrations/hollerau/types.ts` with EXACTLY this content (byte for byte - our backend
repo diffs this file against its own copy to detect drift; do not reformat or edit it):

```ts
// Row shapes of the Supabase schema in db/migrations/001_init.sql.
// Keep in sync with the migration and with starter-kit/hollerau/types.py.
// NUMERIC columns arrive from PostgREST as numbers; TIMESTAMPTZ as ISO-8601 strings.

export type Environment = "sim" | "practice" | "final";

export type CaseStatus = "active" | "deal" | "walked_away" | "no_deal" | "error";

export type MoveAction = "send" | "accept" | "walk_away";

/** A term sheet as the arena sends it; every field is optional because sheets can be partial. */
export interface Terms {
  unit_price?: number | null;
  volume_per_year?: number | null;
  contract_months?: number | null;
  payment_days?: number | null;
  lead_time_days?: number | null;
  incoterm?: string | null;
  index_clause?: string | null;
  tooling_eur?: number | null;
  effective_date?: string | null;
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

Use these types everywhere; delete the hand-written `CaseRow` / `AuditRow` types in
`src/lib/command.ts`. No `any`, no `as unknown as` casts.

## 3. Schema (already exists - do not create or migrate tables)
- `suppliers` (id, name, country ISO-2 like "DE", category, abc_class)
- `cases` - one per played case. Key `session_id`. `environment` is "sim" | "practice" | "final";
  `wave` is 1-5 only in the final. `category_goal` ("leverage" | "stabilise" | "secure_supply" |
  ...) is the procurement segment - it replaces the old `supplier.segment`. `supplier_ids` lists the
  suppliers invited to the case (a case can have several). `c_best` and `score` are NULL until the
  case ends.
- `audit_logs` - one row per buyer move, per supplier thread: `supplier_id`, `turn_number`,
  `action` ("send" | "accept" | "walk_away"), `seconds_left`, `supplier_terms` / `proposed_terms`
  (JSON term sheets), `c_supplier_offer` / `c_proposed` (€), `concession_velocity`,
  `supplier_mindset`, `observed_barrier`, `strategic_intent`, `mathematical_justification`,
  `message_subject`, `message_body`.
- View `case_overview` - one row per case = all `cases` columns + the newest move's live state
  (`moves`, `last_turn`, `last_move_at`, `last_supplier_id`, `last_action`, `last_seconds_left`,
  `last_mindset`, `last_concession_velocity`, `last_c_supplier_offer`, `last_c_proposed`).
- View `wave_scores` - per environment and wave: `cases_played`, `deals`, `avg_score`,
  `total_score`.

Old → new names: `wave_number` → `wave`; `final_score` / `current_score` → `score`;
`c_best_floor` → `c_best`; `c_current_offer` → `last_c_supplier_offer` (case_overview);
`seconds_left` on the case → `last_seconds_left` (case_overview); `supplier_price_offered` →
`c_supplier_offer`; `calculated_local_cost` → `c_proposed`; `raw_email_sent` → `message_body`;
`supplier.segment` → `case.category_goal`.

## 4. Behaviour per view
- **Wave monitor / grid**: read `case_overview` (not `cases`). Add an environment filter
  (sim / practice / final, default: the most recent environment with rows) and a wave filter.
  Countdown: start from `last_seconds_left` at `last_move_at` and tick down locally; show "-" when
  NULL. Show supplier names by looking up `supplier_ids` in `suppliers`.
- **Audit view (`/audit/$sessionId`)**: audit rows ordered by `created_at`, grouped or labelled by
  `supplier_id` (one thread per supplier). Show the term sheets as small key/value tables.
- **Briefing (`/briefing/$sessionId`)**: build its text from `strategic_intent` +
  `mathematical_justification`. Keep the ElevenLabs placeholder.
- **Scoreboard**: read `wave_scores`.
- **Realtime**: subscribe to `cases` and `audit_logs` (views do not emit events) and invalidate the
  `case_overview` / audit queries on any change.

## 5. No score maths in the frontend
Delete `envelopeScore`. Show `score` exactly as stored (NULL → "pending"). Euro values are shown
as stored; formatting (`eur`, `clock`) is fine. Do not compute scores, savings percentages or cost
envelopes in the UI - the backend's cost engine owns all of that.

## 6. Done when
- The app builds, `vitest` passes, `tsc --noEmit` is clean.
- Every page renders against empty tables without errors.
- Nothing in the app references the old column names.
