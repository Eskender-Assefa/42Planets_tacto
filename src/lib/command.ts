import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { hollerau } from "@/integrations/hollerau/client";
import type { AuditLog, CaseOverview, Environment, Supplier, WaveScore } from "@/integrations/hollerau/types";

export const eur = (n: number | null | undefined) =>
  n == null
    ? "-"
    : new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);

export const clock = (s: number) =>
  `${String(Math.floor(Math.max(0, s) / 60)).padStart(2, "0")}:${String(Math.max(0, s) % 60).padStart(2, "0")}`;

/** Score is owned by the backend cost engine; show it exactly as stored. */
export const scoreLabel = (s: number | null | undefined) => (s == null ? "-" : s.toFixed(3));

/** Seconds remaining, ticking down locally from the last move's snapshot. */
export function secondsRemaining(c: CaseOverview, now = Date.now()): number | null {
  if (c.status !== "active" || c.last_seconds_left == null || c.last_move_at == null) return null;
  const elapsed = (now - new Date(c.last_move_at).getTime()) / 1000;
  return Math.max(0, c.last_seconds_left - elapsed);
}

function useRealtime(tables: string[], keys: string[][]) {
  const qc = useQueryClient();
  useEffect(() => {
    const ch = tables.reduce(
      (channel, table) =>
        channel.on("postgres_changes", { event: "*", schema: "public", table }, () => {
          keys.forEach((k) => qc.invalidateQueries({ queryKey: k }));
        }),
      hollerau.channel(`hollerau-${Math.random().toString(36).slice(2)}`),
    );
    ch.subscribe();
    return () => {
      hollerau.removeChannel(ch);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

/** Most recent environment that has any cases; used as the default filter. */
function useLatestEnvironment() {
  return useQuery({
    queryKey: ["hollerau", "latest-env"],
    queryFn: async (): Promise<Environment | null> => {
      const { data, error } = await hollerau
        .from("cases")
        .select("environment")
        .order("started_at", { ascending: false })
        .limit(1);
      if (error) throw error;
      return data[0]?.environment ?? null;
    },
  });
}

export function useSuppliers() {
  return useQuery({
    queryKey: ["hollerau", "suppliers"],
    queryFn: async (): Promise<Map<string, Supplier>> => {
      const { data, error } = await hollerau.from("suppliers").select("*");
      if (error) throw error;
      return new Map(data.map((s) => [s.id, s]));
    },
  });
}

export function supplierNames(c: CaseOverview, suppliers: Map<string, Supplier> | undefined): string {
  if (!c.supplier_ids.length) return "-";
  return c.supplier_ids.map((id) => suppliers?.get(id)?.name ?? id).join(", ");
}

export function useCaseOverview(environment: Environment | null, wave: number | null) {
  useRealtime(["cases", "audit_logs"], [["hollerau"]]);
  const latest = useLatestEnvironment();
  const env = environment ?? latest.data ?? null;
  return {
    latestEnvironment: latest.data ?? null,
    query: useQuery({
      queryKey: ["hollerau", "case_overview", env, wave],
      enabled: env != null,
      queryFn: async (): Promise<CaseOverview[]> => {
        if (env == null) return [];
        let q = hollerau
          .from("case_overview")
          .select("*")
          .eq("environment", env)
          .order("started_at", { ascending: false });
        if (wave != null) q = q.eq("wave", wave);
        const { data, error } = await q;
        if (error) throw error;
        return data;
      },
    }),
  };
}

export function useCase(sessionId: string) {
  useRealtime(["cases", "audit_logs"], [["hollerau"]]);
  const c = useQuery({
    queryKey: ["hollerau", "case", sessionId],
    queryFn: async (): Promise<CaseOverview | null> => {
      const { data, error } = await hollerau
        .from("case_overview")
        .select("*")
        .eq("session_id", sessionId)
        .maybeSingle();
      if (error) throw error;
      return data;
    },
  });
  const logs = useQuery({
    queryKey: ["hollerau", "audit", sessionId],
    queryFn: async (): Promise<AuditLog[]> => {
      const { data, error } = await hollerau
        .from("audit_logs")
        .select("*")
        .eq("session_id", sessionId)
        .order("created_at");
      if (error) throw error;
      return data;
    },
  });
  return { c, logs };
}

export function useWaveScores() {
  useRealtime(["cases"], [["hollerau"]]);
  return useQuery({
    queryKey: ["hollerau", "wave_scores"],
    queryFn: async (): Promise<WaveScore[]> => {
      const { data, error } = await hollerau
        .from("wave_scores")
        .select("*")
        .order("environment")
        .order("wave");
      if (error) throw error;
      return data;
    },
  });
}
