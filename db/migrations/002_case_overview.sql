-- Hollerau Agentic Command - dashboard read model. Run after 001_init.sql. Safe to re-run.
--
-- A case can have several supplier threads, and the live state (clock, latest offer, mindset)
-- lives on the newest audit row. case_overview serves one row per case with that state attached,
-- so the dashboard needs no joins or arithmetic of its own.
-- Realtime does not fire on views: subscribe to `cases` and `audit_logs`, then refetch the view.

-- Suppliers invited to the case, known when the case opens (the arena's case.suppliers).
ALTER TABLE public.cases ADD COLUMN IF NOT EXISTS supplier_ids TEXT[] NOT NULL DEFAULT '{}';

CREATE OR REPLACE VIEW public.case_overview
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
       last.c_proposed             AS last_c_proposed
FROM public.cases c
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS moves FROM public.audit_logs a WHERE a.session_id = c.session_id
) n ON true
LEFT JOIN LATERAL (
    SELECT a.turn_number, a.created_at, a.supplier_id, a.action, a.seconds_left,
           a.supplier_mindset, a.concession_velocity, a.c_supplier_offer, a.c_proposed
    FROM public.audit_logs a
    WHERE a.session_id = c.session_id
    ORDER BY a.created_at DESC, a.id DESC
    LIMIT 1
) last ON true;
