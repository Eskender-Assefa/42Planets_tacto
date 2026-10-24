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
