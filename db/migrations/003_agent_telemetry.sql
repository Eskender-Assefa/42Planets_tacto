-- Hollerau Agentic Command - agent telemetry. Run after 002_case_overview.sql. Safe to re-run.
--
-- The Hollerau agent logs, per move, the envelope it computed (target, floor estimate, supplier-
-- health charge at the supplier's offer), the arena's claim verdicts and where the decision came
-- from (Claude, a deterministic fallback, the time-cap close). Cases get their protocols.

ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS c_target         NUMERIC(14, 2);  -- C of the sheet we aimed for
ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS c_floor_est      NUMERIC(14, 2);  -- C at the supplier's estimated floor
ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS penalty_at_offer NUMERIC(14, 2);  -- est. supplier-health charge in the supplier's offer
ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS claims           JSONB;           -- {"verified": n, "contradicted": n, ...}
ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS decision_source  TEXT
    CHECK (decision_source IS NULL OR decision_source IN ('claude', 'fallback', 'rule', 'closing', 'naive'));
ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS llm_latency_ms   INT;

ALTER TABLE public.cases ADD COLUMN IF NOT EXISTS segment_protocol TEXT;  -- e.g. 'Strategic - Safeguard Protocol'
ALTER TABLE public.cases ADD COLUMN IF NOT EXISTS culture_protocol TEXT;  -- e.g. 'Low-Context / Direct Specification'

-- c.* changes shape with the new case columns: a view's columns cannot be reordered in place.
DROP VIEW IF EXISTS public.case_overview;
CREATE VIEW public.case_overview
WITH (security_invoker = true) AS
SELECT c.*,
       COALESCE(n.moves, 0)        AS moves,
       last.turn_number            AS last_turn,
       last.created_at             AS last_move_at,
       last.supplier_id            AS last_supplier_id,
       last.action                 AS last_action,
       last.seconds_left           AS last_seconds_left,
       last.supplier_mindset       AS last_mindset,
       last.concession_velocity    AS last_concession_velocity,
       last.c_supplier_offer       AS last_c_supplier_offer,
       last.c_proposed             AS last_c_proposed,
       last.c_target               AS last_c_target,
       last.c_floor_est            AS last_c_floor_est,
       last.decision_source        AS last_decision_source
FROM public.cases c
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS moves FROM public.audit_logs a WHERE a.session_id = c.session_id
) n ON true
LEFT JOIN LATERAL (
    SELECT a.turn_number, a.created_at, a.supplier_id, a.action, a.seconds_left,
           a.supplier_mindset, a.concession_velocity, a.c_supplier_offer, a.c_proposed,
           a.c_target, a.c_floor_est, a.decision_source
    FROM public.audit_logs a
    WHERE a.session_id = c.session_id
    ORDER BY a.created_at DESC, a.id DESC
    LIMIT 1
) last ON true;
