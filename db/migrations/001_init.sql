-- Hollerau Agentic Command - initial schema.
-- Run once in the Supabase SQL Editor (or `supabase db push`). Safe to re-run: every object is
-- created only if missing.
--
-- Write path: the Python runner uses the service-role key (bypasses RLS).
-- Read path: the Lovable dashboard uses the anon key and may only SELECT.
-- No money is computed here except the score aggregation view; per-turn costs are written by the
-- runner from arena_kit.cost.total_cost.

-- 1. Supplier master data, mirrored from data/package/world.sqlite (suppliers table).
CREATE TABLE IF NOT EXISTS public.suppliers (
    id          TEXT PRIMARY KEY,                 -- e.g. 'sup:70110'
    name        TEXT NOT NULL,
    country     TEXT,                             -- ISO-2, e.g. 'DE'
    category    TEXT,                             -- e.g. 'castings'
    abc_class   TEXT,                             -- 'A' | 'B' | 'C'
    synced_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. One row per played case (one arena session).
CREATE TABLE IF NOT EXISTS public.cases (
    session_id      TEXT PRIMARY KEY,             -- arena session id, e.g. 'sim1'
    case_id         TEXT NOT NULL,                -- e.g. 'case:S01'
    environment     TEXT NOT NULL CHECK (environment IN ('sim', 'practice', 'final')),
    wave            INT,                          -- Live Final wave 1-5; NULL outside the final
    title           TEXT,
    case_type       TEXT,                         -- e.g. 'price_increase'
    category_goal   TEXT,                         -- e.g. 'leverage' | 'stabilise' | 'secure_supply'
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'deal', 'walked_away', 'no_deal', 'error')),
    deal_supplier_id TEXT REFERENCES public.suppliers(id),
    c_open          NUMERIC(14, 2),               -- known from the opening quotes
    c_alt           NUMERIC(14, 2),               -- the buyer's alternative, if any
    c_best          NUMERIC(14, 2),               -- only revealed in the final result
    c_deal          NUMERIC(14, 2),
    score           NUMERIC(6, 4) CHECK (score IS NULL OR score BETWEEN 0 AND 1),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at        TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS cases_env_wave_idx ON public.cases (environment, wave);

-- 3. Traceability: one row per buyer move, written BEFORE the move is sent to the arena.
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id                          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id                  TEXT NOT NULL REFERENCES public.cases(session_id) ON DELETE CASCADE,
    supplier_id                 TEXT NOT NULL REFERENCES public.suppliers(id),
    turn_number                 INT NOT NULL CHECK (turn_number >= 1),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    seconds_left                INT,              -- NULL when the case has no clock
    action                      TEXT NOT NULL CHECK (action IN ('send', 'accept', 'walk_away')),
    supplier_terms              JSONB,            -- supplier's standing term sheet
    proposed_terms              JSONB,            -- terms we put forward this move
    c_supplier_offer            NUMERIC(14, 2),   -- total_cost of supplier_terms
    c_proposed                  NUMERIC(14, 2),   -- total_cost of proposed_terms
    concession_velocity         NUMERIC(10, 6),
    supplier_mindset            TEXT,             -- e.g. 'stalled' | 'yielding' | 'critical_breakoff'
    observed_barrier            TEXT NOT NULL,
    strategic_intent            TEXT NOT NULL,
    mathematical_justification  TEXT NOT NULL,
    message_subject             TEXT,
    message_body                TEXT,             -- NULL for accept / walk_away
    -- a retried write must not log the same move twice
    CONSTRAINT audit_logs_move_unique UNIQUE (session_id, supplier_id, turn_number)
);
CREATE INDEX IF NOT EXISTS audit_logs_session_idx ON public.audit_logs (session_id, created_at);

-- 4. Scoreboard: case scores (0-1 each) aggregated per environment and wave. Converting to
--    tournament points is left to the dashboard once the official points rule is confirmed.
CREATE OR REPLACE VIEW public.wave_scores
WITH (security_invoker = true) AS
SELECT environment,
       wave,
       COUNT(*)                                  AS cases_played,
       COUNT(*) FILTER (WHERE status = 'deal')   AS deals,
       ROUND(AVG(score), 4)                      AS avg_score,
       ROUND(SUM(COALESCE(score, 0)), 4)         AS total_score
FROM public.cases
GROUP BY environment, wave;

-- 5. Row-level security: anon/authenticated may read, nobody but the service role may write.
ALTER TABLE public.suppliers  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cases      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'read_suppliers') THEN
        CREATE POLICY read_suppliers  ON public.suppliers  FOR SELECT TO anon, authenticated USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'read_cases') THEN
        CREATE POLICY read_cases      ON public.cases      FOR SELECT TO anon, authenticated USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'read_audit_logs') THEN
        CREATE POLICY read_audit_logs ON public.audit_logs FOR SELECT TO anon, authenticated USING (true);
    END IF;
END $$;

-- 6. Realtime: the dashboard subscribes to new cases and audit rows.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_publication_tables
                   WHERE pubname = 'supabase_realtime' AND tablename = 'cases') THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.cases;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_publication_tables
                   WHERE pubname = 'supabase_realtime' AND tablename = 'audit_logs') THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.audit_logs;
    END IF;
END $$;
