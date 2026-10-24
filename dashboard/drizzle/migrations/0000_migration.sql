CREATE TABLE public.suppliers (
  id text PRIMARY KEY,
  name text NOT NULL,
  segment text NOT NULL,
  country text NOT NULL,
  historical_base_cost numeric(12,2) NOT NULL DEFAULT 0
);
CREATE TABLE public.cases (
  session_id text PRIMARY KEY,
  supplier_id text REFERENCES public.suppliers(id),
  wave_number int NOT NULL DEFAULT 1,
  turn_number int NOT NULL DEFAULT 0,
  seconds_left int NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'Active',
  c_open numeric(12,2) NOT NULL,
  c_current_offer numeric(12,2) NOT NULL,
  c_best_floor numeric(12,2) NOT NULL,
  current_score numeric(6,3) NOT NULL DEFAULT 0,
  final_score numeric(6,3),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.audit_logs (
  id bigserial PRIMARY KEY,
  session_id text REFERENCES public.cases(session_id) ON DELETE CASCADE,
  turn_number int NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  supplier_price_offered numeric(12,2),
  calculated_local_cost numeric(12,2),
  concession_velocity numeric(8,4),
  supplier_mindset text,
  observed_barrier text NOT NULL,
  strategic_intent text NOT NULL,
  mathematical_justification text NOT NULL,
  raw_email_sent text NOT NULL DEFAULT ''
);
GRANT SELECT ON public.suppliers, public.cases, public.audit_logs TO anon, authenticated;
GRANT ALL ON public.suppliers, public.cases, public.audit_logs TO service_role;
GRANT USAGE ON SEQUENCE public.audit_logs_id_seq TO service_role;
ALTER TABLE public.suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public read" ON public.suppliers FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public.cases FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public.audit_logs FOR SELECT TO anon, authenticated USING (true);
ALTER PUBLICATION supabase_realtime ADD TABLE public.cases;
ALTER PUBLICATION supabase_realtime ADD TABLE public.audit_logs;

INSERT INTO public.suppliers VALUES
('brandlhuber_01','Gießerei Brandlhuber','Strategic Partner','Germany',138000),
('ferroni_02','Ferroni Metalli S.p.A.','Leverage','Italy',96000),
('takeda_03','Takeda Precision Works','Bottleneck','Japan',210000),
('nordstahl_04','Nordstahl AG','Leverage','Germany',74000),
('lyon_05','Forges de Lyon','Strategic Partner','France',158000),
('kowalski_06','Kowalski Odlewnia','Leverage','Poland',61000),
('svensk_07','Svensk Gjuteri AB','Bottleneck','Sweden',122000),
('brno_08','Brno Strojírny','Leverage','Czechia',54000),
('alpen_09','Alpenguss GmbH','Strategic Partner','Austria',189000),
('hollandia_10','Hollandia Castings BV','Bottleneck','Netherlands',101000);

INSERT INTO public.cases (session_id,supplier_id,wave_number,turn_number,seconds_left,status,c_open,c_current_offer,c_best_floor,current_score,final_score) VALUES
('case_wave1_01','ferroni_02',1,6,188,'Active',98000,90200,86000,0.650,NULL),
('case_wave1_02','takeda_03',1,3,402,'Active',215000,211000,195000,0.200,NULL),
('case_wave1_03','nordstahl_04',1,8,0,'Closed',76000,69800,68000,0.775,0.775),
('case_wave1_04','brandlhuber_01',1,4,312,'Active',142000,131500,122000,0.525,NULL),
('case_wave1_05','lyon_05',1,5,47,'Active',160000,151000,144000,0.563,NULL),
('case_wave1_06','kowalski_06',1,7,221,'Active',63000,58100,56500,0.754,NULL),
('case_wave1_07','svensk_07',1,2,488,'Active',125000,124000,112000,0.077,NULL),
('case_wave1_08','brno_08',1,9,0,'Failed',56000,56000,50000,0.000,0.000),
('case_wave1_09','alpen_09',1,4,276,'Active',192000,183500,172000,0.425,NULL),
('case_wave1_10','hollandia_10',1,3,355,'Active',104000,100800,94000,0.320,NULL);

INSERT INTO public.audit_logs (session_id,turn_number,supplier_price_offered,calculated_local_cost,concession_velocity,supplier_mindset,observed_barrier,strategic_intent,mathematical_justification,raw_email_sent) VALUES
('case_wave1_04',1,142000,142000,0,'Yielding','Opening quote anchored at list price.','Anchor low with volume commitment over 24 months.','Volume lever projects −6% on unit cost.','Dear Herr Brandlhuber, thank you for your quote...'),
('case_wave1_04',2,136000,135400,0.042,'Yielding','Supplier accepts volume framing, resists on alloy surcharge.','Decouple alloy index from base price.','Index-linked surcharge cuts expected cost by €4.1k.','We propose tying the alloy component to the LME index...'),
('case_wave1_04',3,132000,131900,0.029,'Yielding','Concession pace slowing near cost ceiling.','Test floor with delivery flexibility.','Flexible lead time worth est. €2.0k to supplier.','Could a 6-week delivery window help your planning?'),
('case_wave1_04',4,131500,131500,0.004,'Stalled','Supplier hit a hard cost ceiling on base unit castings.','Squeezing unit price is blocked. Shifting variables to an early liquidity lever.','Interest penalty offset by supplier baseline drop, netting +0.18 optimization.','We can offer payment within 10 days in exchange for...'),
('case_wave1_05',5,151000,150600,0.011,'Stalled','French counterpart insists on formal escalation.','Move to written proposal with director in copy.','Escalation protects 0.56 score floor.','Madame, veuillez trouver ci-joint notre proposition...');