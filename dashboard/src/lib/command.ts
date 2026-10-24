import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";

export type CaseRow = {
  session_id: string;
  wave_number: number;
  turn_number: number;
  seconds_left: number;
  status: string;
  c_open: number;
  c_current_offer: number;
  c_best_floor: number;
  current_score: number;
  final_score: number | null;
  supplier: { id: string; name: string; segment: string; country: string } | null;
  mindset?: string | null;
};

export type AuditRow = {
  id: number;
  session_id: string | null;
  turn_number: number;
  created_at: string;
  supplier_price_offered: number | null;
  calculated_local_cost: number | null;
  concession_velocity: number | null;
  supplier_mindset: string | null;
  observed_barrier: string;
  strategic_intent: string;
  mathematical_justification: string;
  raw_email_sent: string;
};

/** Score = share of the way from opening cost to best floor (0..1). */
export function envelopeScore(open: number, current: number, floor: number) {
  const span = open - floor;
  if (span <= 0) return 0;
  return Math.max(0, Math.min(1, (open - current) / span));
}

export const eur = (n: number | null | undefined) =>
  n == null
    ? "—"
    : new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);

export const clock = (s: number) =>
  `${String(Math.floor(Math.max(0, s) / 60)).padStart(2, "0")}:${String(Math.max(0, s) % 60).padStart(2, "0")}`;

function useRealtime(table: string, keys: string[][]) {
  const qc = useQueryClient();
  useEffect(() => {
    const ch = supabase
      .channel(`${table}-${Math.random().toString(36).slice(2)}`)
      .on("postgres_changes", { event: "*", schema: "public", table }, () => {
        keys.forEach((k) => qc.invalidateQueries({ queryKey: k }));
      })
      .subscribe();
    return () => {
      supabase.removeChannel(ch);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [table]);
}

export function useCases() {
  useRealtime("cases", [["cases"]]);
  useRealtime("audit_logs", [["cases"]]);
  return useQuery({
    queryKey: ["cases"],
    queryFn: async (): Promise<CaseRow[]> => {
      const [{ data, error }, { data: logs }] = await Promise.all([
        supabase
          .from("cases")
          .select("*, supplier:suppliers(id,name,segment,country)")
          .order("session_id"),
        supabase.from("audit_logs").select("session_id,turn_number,supplier_mindset").order("turn_number"),
      ]);
      if (error) throw error;
      const mind = new Map<string, string | null>();
      (logs ?? []).forEach((l) => l.session_id && mind.set(l.session_id, l.supplier_mindset));
      return (data ?? []).map((c) => ({ ...(c as unknown as CaseRow), mindset: mind.get(c.session_id) ?? null }));
    },
  });
}

export function useCase(sessionId: string) {
  useRealtime("audit_logs", [["audit", sessionId]]);
  useRealtime("cases", [["case", sessionId]]);
  const c = useQuery({
    queryKey: ["case", sessionId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("cases")
        .select("*, supplier:suppliers(id,name,segment,country)")
        .eq("session_id", sessionId)
        .maybeSingle();
      if (error) throw error;
      return data as unknown as CaseRow | null;
    },
  });
  const logs = useQuery({
    queryKey: ["audit", sessionId],
    queryFn: async (): Promise<AuditRow[]> => {
      const { data, error } = await supabase
        .from("audit_logs")
        .select("*")
        .eq("session_id", sessionId)
        .order("turn_number");
      if (error) throw error;
      return data as AuditRow[];
    },
  });
  return { c, logs };
}

