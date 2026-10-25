# Lovable prompt 004 - negotiation insights: price path, mechanisms, evidence, pitch view

Paste everything below the line into Lovable. No schema change: everything comes from columns that
already exist (`audit_logs`, `cases`, view `case_overview`). Afterwards pull the subtree with
`bash scripts/sync-dashboard.sh`.

---

Our buyer agent got several new mechanisms. Their traces are already in the data we load; make them
visible. The jury reads our negotiations, so the dashboard must explain every move at a glance.

Ground rules, same as before:
- Read-only. No mock data, no placeholder numbers. NULL or missing values render as "-".
- Do NOT change `src/integrations/hollerau/types.ts` (our backend diffs it byte for byte) and do not
  add Supabase tables, columns or queries beyond the existing `cases`, `case_overview`, `audit_logs`
  and `suppliers` reads. Everything below is derived in the frontend from fields we already fetch.
- Keep all existing routes, components and tests working. Use the existing theme tokens, `num` and
  `label-caps` classes and shadcn components; charts with the project's chart setup (recharts via
  shadcn `chart`). Keep it legible in both light and dark mode.
- Put parsing helpers in `src/lib/telemetry.ts` (pure functions with unit tests in `src/test/`).

## 1. Parse the agent's mechanism tags (helper, used everywhere below)

`audit_logs.mathematical_justification` is a " | "-separated string. Besides the existing numbers it
can contain these tags (exact formats; any may be absent; there may be several):

- `claim attached: <kind>` - the one data-backed argument attached to this e-mail. `<kind>` is one of
  `index`, `notice`, `should_cost`, `volume`, `delivery`, `quality`, `history`, `rival_offer`, `news`.
  Show labels: Index fall, Notice period, Cost estimate, Volume forecast, Delivery record, Defect
  rate, Order history, Rival's live offer, Supplier news.
- `paced to min C EUR <amount>: <old>-><new>[, <old>-><new>]` - the agent raised its own price from
  old to new so it concedes at least a minimum step and never goes back. Label: "Paced 5.30 → 5.45".
- `swap offered: <field>=<value> for -<cut>% (break-even -<be>%)` - a trade of a term for a price cut.
  Label: "Trade: <field> <value> for -<cut>%".

Write `parseMechanisms(justification: string): { claimKind: string | null; paced: {from: number; to:
number}[]; swap: {field: string; value: string; cutPct: number} | null }` and test it with these
inputs (expected outputs in the test):
- `"C_open EUR 391,027.40 | ... | claim attached: index"` → claimKind "index"
- `"... | paced to min C EUR 324,997.80: 5.30->5.45 | claim attached: delivery"` → paced
  [{from 5.30, to 5.45}], claimKind "delivery"
- `"... | swap offered: payment_days=14 for -5.0% (break-even -1.7%)"` → swap {payment_days, 14, 5.0}
- `"-"` → all empty

Also write `extractEvidence(body: string | null): { sentence: string; ids: string[] } | null`: the
sentence of the e-mail that contains data IDs, matched with this regex (from our backend):
`/\b(?:idx|quote|offer|sc|qn|po|cost|fc|news|doc|ctr):[\w.:@#/-]*\w/g`. Return the first such
sentence and its IDs; null if none.

`supplier_mindset` can now also be `"unread"` (a switch in the agent turned mindset reading off):
`MindsetBadge` must render it as a neutral "unread" badge, not as an error.

## 2. Audit page (`/audit/$sessionId`): price path chart on top

Above the turn list add a panel "Negotiation path" with a line chart over turns (x = turn_number):
- line A "Supplier offer" = `c_supplier_offer`, line B "Our counter" = `c_proposed` (both in EUR,
  total cost over the contract - lower is better for us), markers on each point;
- horizontal reference lines from the case: "Opening" = `c_open`, "Best possible" = `c_best`,
  "Alternative (no deal)" = `c_alt` (only if not NULL); if the case ended with a deal, a highlighted
  final point "Deal" = `c_deal`;
- y axis formatted like `eur()` in short form (e.g. €1.52M), tooltip with full `eur()` values and the
  turn's decision source;
- one row per supplier when the case has several suppliers (RFQ): either a small multiple per
  supplier or a supplier selector - lines must never mix suppliers.
Under the chart one sentence, computed: "Captured X % of the possible saving · €Y left vs best
possible", X = `score` × 100 (1 decimal), Y = `c_deal − c_best` (only for deals).

## 3. Audit page: per-turn mechanism strip and evidence card

In each turn card, section "3 · Decision", above "Strategic intent":
- a row of chips from `parseMechanisms`: the claim chip (e.g. "📎 Index fall"), each paced move
  ("↗ Paced 5.30 → 5.45"), the trade chip, and a "Python rule" chip when `decision_source` = "rule"
  showing `observed_barrier` as its tooltip (e.g. "Supplier declared its final offer.").
- an "Evidence" card when `extractEvidence(message_body)` finds a sentence: the sentence with every
  data ID rendered as a monospace pill. Below it the case's running claim tally from `claims`
  (verified / irrelevant / contradicted / duplicate) - keep the existing `ClaimChips`.
Keep the existing e-mail block; highlight the evidence sentence inside it with a subtle background.

## 4. Home / case list: a "how we negotiate" summary per case

In the case table (home route) add three compact columns, derived from that case's audit rows
(fetch audit rows per case only when the row is expanded or visible - no N+1 storm on page load;
a single `audit_logs` query filtered by the listed session_ids is fine):
- "Claims" - verified / total from the newest row's `claims` (e.g. "4/4"), red if any contradicted;
- "Moves" - number of our counters and how many were paced (e.g. "5 · 2 paced");
- "Left on table" - `c_deal − c_best` for deals (EUR, short form), "-" otherwise.

## 5. Scoreboard: where the points are

On `/scoreboard` add a horizontal bar chart "Score by case" for the selected environment: one bar
per case (label `case_id` + `case_type`), value = best `score` per case_id (0-1 shown as 0-100),
sorted ascending so the weakest cases are on top; bar colour by `case_type` using one consistent
categorical palette with a legend; a vertical reference line at the mean. Clicking a bar opens that
case's audit page (newest session for that case_id).

## 6. Pitch view (`/pitch/$sessionId`, linked from the audit page header)

A clean, large-type, read-only page for presenting one negotiation to a jury:
- title, supplier names, case type, category goal, final score as a big number;
- the price path chart from section 2, full width;
- a vertical "story" list, one line per turn: "Turn n · <supplier> offered <supplier unit price> ·
  we countered <our unit price> · <claim label or '-'> · <mechanism chips>", unit prices from
  `supplier_terms.unit_price` and `proposed_terms.unit_price` (2 decimals, "-" if missing);
- the final terms of the deal (last `proposed_terms` or the accepted supplier terms) with
  `TermSheet`.
No navigation chrome besides a small "← back to audit" link; must print well (A4 landscape).

## Done when
- all existing tests pass, the new helper tests pass, `bun run build` succeeds;
- with real data: the P07 audit shows the path chart, "📎 …" claim chips on each counter, and a
  "↗ Paced …" chip on turns where the agent raised its price.
