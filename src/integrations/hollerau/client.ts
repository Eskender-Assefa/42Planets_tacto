import { createClient } from "@supabase/supabase-js";
import { HOLLERAU_SUPABASE_URL, HOLLERAU_SUPABASE_ANON_KEY } from "./config";
import type { AuditLog, Case, CaseOverview, Supplier, WaveScore } from "./types";

type ReadOnlyTable<R> = { Row: R; Insert: never; Update: never; Relationships: [] };

type HollerauDatabase = {
  public: {
    Tables: {
      suppliers: ReadOnlyTable<Supplier>;
      cases: ReadOnlyTable<Case>;
      audit_logs: ReadOnlyTable<AuditLog>;
      case_overview: ReadOnlyTable<CaseOverview>;
      wave_scores: ReadOnlyTable<WaveScore>;
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
};

/** Read-only client for the Hollerau negotiation backend. The dashboard never writes. */
export const hollerau = createClient<HollerauDatabase>(HOLLERAU_SUPABASE_URL, HOLLERAU_SUPABASE_ANON_KEY, {
  auth: { persistSession: false, autoRefreshToken: false },
});
