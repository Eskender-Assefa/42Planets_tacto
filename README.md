# 42Planets · Hollerau Agentic Command

**An autonomous procurement negotiator for the [Tacto Negotiation Arena](https://arena.tacto.ai/live)**
(Industrial Agents Hackathon 2026 · MM × UVC × Anthropic).

Our agent is the buyer at *Hollerau Pumpenwerke*, a fictional German pump maker. Each case starts with
one supplier e-mail: a foundry wants +9.5 %, a contract expires, a new pump needs three quotes. The
agent reads three years of company data, negotiates by e-mail with Tacto's multi-agent supplier bots,
and signs the deal with the lowest **total cost**, or walks away when no deal beats the alternative.
No human in the loop.

> **Python computes, Claude decides and writes.** Every euro comes from the arena's own cost function,
> every cited figure comes from the data the suppliers check against, and every move is written to an
> audit log *before* it is sent.

---

## Contents

- [Results](#results)
- [How it works](#how-it-works)
- [What makes it negotiate well](#what-makes-it-negotiate-well)
- [Traceability: audit log, dashboard, voice briefing](#traceability-audit-log-dashboard-voice-briefing)
- [Run it](#run-it)
- [Configuration switches](#configuration-switches)
- [Tests and quality gates](#tests-and-quality-gates)
- [What we learned (including what did not work)](#what-we-learned-including-what-did-not-work)
- [Repository layout](#repository-layout)
- [Credits and licence](#credits-and-licence)

---

## Results

The score of a case is the share of the possible saving the deal captures:
`score = (C_open − C_deal) / (C_open − C_best)`, where C is the total cost over the contract (price,
payment days, freight, quality, lead time, coverage, index clauses, supplier health).

**Practice arena, 10 hosted cases, full runs:**

| Stage | 10-case total | What changed |
|---|---|---|
| First Claude agent (practice run 1) | 47.1 | zeros from pushing past final offers and RFQ thread timeouts |
| `post-guard` | 55.8 | concession guard, coverage checks, walk-away rule |
| `post-winners-fix` | 69.8 | one checked claim per message, owner payment terms, capacity rule |
| `post-release` + RFQ fix | **≈72.7** | concession path, reciprocity, swap guard, Sunday release, new-supplier claims |

Practice leaderboard (mean of the best score per case): **75.7**. Our best per case:

| Case | Type | Best | | Case | Type | Best |
|---|---|---|---|---|---|---|
| P01 | price increase | 0.93 | | P07 | bundling | 0.73 |
| P02 | price increase (strategic) | 0.79 | | P08 | raw material | 0.65 |
| P03 | renewal | 0.94 | | P10 | capacity | 0.69 |
| P04 | renewal | 0.86 | | P11 | quality | 0.48 |
| P05 | RFQ, 3 suppliers | 0.82 | | P18 | raw material | 0.69 |

**Live Final** (Sunday 13:30, five waves of hidden cases with new suppliers): results on
[arena.tacto.ai/results](https://arena.tacto.ai/results).

---

## How it works

Every turn of every negotiation runs the same pipeline (`starter-kit/hollerau/negotiator.py`):

```
 supplier e-mail + term sheet
            │
 1 INGEST   │  thread, attachments (quote PDF, cost breakdown), the case file
 2 TELEMETRY│  concession velocity, supplier mindset, claim verdicts        telemetry.py
 3 ENVELOPE │  C of every offer, our target, the supplier's floor estimate,  envelope.py
            │  what each lever (payment, index clause, volume, ...) is worth   (arena_kit.cost)
 4 DECIDE   │  Python rules first (accept a final offer, walk when the       negotiator.py
            │  alternative is cheaper, close at the wave cap) - otherwise
            │  Claude returns ONE schema-enforced JSON: reasoning + decision
 5 GATES    │  concession guard, concession path (never retract), forced     negotiator.py
            │  trades, exactly one checked claim attached                     claims.py
 6 RECORD   │  audit row with the full reasoning -> Supabase, BEFORE sending  recorder.py
            ▼
 e-mail + 1-3 term sheets to the supplier
```

- **Claude never computes.** The prompt carries every number it may use (C of each sheet, target,
  lever values, the next claim sentence); the audit's `mathematical_justification` is written by
  Python from the engine's numbers. Model: Claude Opus 5.5 at low effort with server-side fallback,
  about €0.80 per 10-case run.
- **The cost function is the arena's own** (`arena_kit.cost.total_cost`), so the agent ranks offers
  exactly as the scorer does - including terms a human buyer would overlook. (In the EHL final on the
  same arena, a team "won" a price cut on H03 and scored 0: the supplier had quietly shortened
  payment from 90 to 14 days.)
- **Deterministic fallbacks everywhere.** Claude down, slow or vetoed → a counter at the engine's
  target; a bug in our layer → the kit's naive move keeps the case alive; the wave cap near → close
  on the best sheet that beats the alternative, else walk.

---

## What makes it negotiate well

Most of these came from reading replays - ours and those of the top three teams of the EHL final on
the same arena (`docs/winners_analysis/`).

### 1. One checked claim per message (`claims.py`)

The arena checks every data ID an e-mail cites against `facts.json`. Suppliers conceded about **2.3 %**
after a message with one new verified claim, about **0.3 %** after one without, and three claims in
one message moved them only about 5 %. So Python writes the claim sentences - every figure copied from
the facts - and attaches exactly one new claim to each offer, strongest first:

| Claim | Cites | Example |
|---|---|---|
| Index fall | 2 × `idx` of one of the part's cost drivers, ≤ 12 months apart, ending within the last 12 months of the data | "The index AS-14404 changed −8.5 % from 2024-11 to 2025-10 (idx:…, idx:…)." |
| Notice period | the supplier's letter `doc` + our contract `ctr` | "Your letter … gives us 51 days of notice, while our agreement … requires 90 days." |
| Cost estimate | `cost` | "Our bottom-up estimate of the full cost is EUR 132.64 per unit before margin (…)." |
| Volume forecast | `fc` | "Our forecast … expects 8150 units a year, a change of +10.1 %." |
| Delivery / defect record | `sc` | "Your rolling twelve-month on-time delivery in 2026Q3 was 85.2 % (…)." |
| Order history | 2-8 × `po` of the part | "Our last 3 orders for this part were at EUR 126.53 (…)." |
| Rival's live offer (RFQ) | another bidder's `offer` | "Another bidder in this tender currently offers EUR 29.00 per unit (…)." |

Rules learned live, each from a failed claim: an index window needs **both** IDs; only the part's own
cost drivers count; "the last 12 months" runs from the newest month of all index data; never cite a
supplier's own offer back to it; and **no thousands separators** - the arena read "2,376 ppm" as 2.376
and marked the claim *contradicted*. Result: 31 of 32 claims verified in the last full run, up from
6 of 18.

### 2. Move every round, never take a concession back

The arena's rule is *"no concession without a move from you."* Our early agent held its price flat for
three rounds and got final offers by round 2-3. Now every counter concedes at least a shrinking share
of the gap to the supplier's offer (25 % → 8 %, measured in total cost, so any package shape compares),
never costs us less than our previous counter, and keeps terms already agreed. **Reciprocity:** if the
supplier did not move, we may hold. **In an RFQ** the step never lifts us above a cheaper rival's
live offer.

### 3. Close and walk at the right moment

- A supplier's **final offer** is accepted when it is the cheapest live offer and beats both the
  opening and our alternative. (We tested switching this off: 4 of 5 suppliers walked away the moment
  we pushed past their final offer.)
- An **agreed** sheet is accepted only when no other live supplier is cheaper.
- **Walk away** when every final offer costs more than the alternative - no deal then scores better.
- Never accept a sheet that leaves need uncovered while contract length or volume is still negotiable.
- The last message and the wave cap always close on the best sheet that beats the alternative.

### 4. Terms that fit the supplier

- **Total-cost packages:** for each target price the engine searches every lever combination
  (payment days, contract months, volume, index clause, incoterm, effective date, ppm, chargeback) and
  prices the supplier's own alternatives - proposing one back when it is cheaper for us.
- **Owner-run and cash-short suppliers** (sender "Owner, …", or a credit cut / lost customer / payment
  letter in the Sunday release) get short payment terms, which they value far above our interest
  cost - but not in strategic cases, where our own tests measured 90 days ahead.
- **Capacity cases:** never ask a shorter lead time than the supplier offers (it prices an overtime
  premium).
- **Trades, not gifts:** a lever the supplier wants is only given for a price cut of at least 1.5×
  our break-even (`swaps.py`), and a forced trade may never concede past the concession guard.
- **Protocols:** each case's category goal (leverage, stabilise, secure supply, quality first,
  routine) sets anchor depth and tone; the supplier's country sets the culture protocol; the
  supplier's floor is calibrated on every practice result the arena revealed (`calibrate.py`).

### 5. Robust for the Live Final

- **New suppliers** not in the data package: claims are built per kind and from the case file's own
  facts, so a missing record never costs the rest.
- **Sunday market release** (`uv run arena data`): news and letters are citable and feed the
  cash-short rule and Claude's optional news pick.
- **RFQs:** every bidder's thread is answered within the 60-second rule (three late replies end a
  thread).
- **Crashes:** a case that fails mid-play still gets its outcome stored from the arena.

---

## Traceability: audit log, dashboard, voice briefing

- **Write-first audit (`recorder.py`).** Before any message reaches a supplier, a row lands in
  Supabase `audit_logs`: supplier terms, our terms, both costs, target, floor estimate, claim
  verdicts, decision source (Claude / rule / fallback / closing), latency and the reasoning:
  `observed_barrier`, `strategic_intent`, `mathematical_justification` (with tags such as
  `claim attached: index` and `paced to min C …: 5.30->5.45`). No row, no send.
- **Dashboard** ([Lovable](https://lovable.dev), git subtree in `dashboard/`, read-only on Supabase):
  live wave view, per-case audit with a negotiation-path chart, mechanism chips and evidence cards,
  a score-by-case scoreboard, and a printable **pitch view** per negotiation.
- **Voice briefing** in the browser (Web Speech API, no external service): a spoken summary or a
  round-by-round narration of any negotiation, plus optional live narration during the final.

---

## Run it

### Requirements

Python 3.12, [uv](https://docs.astral.sh/uv/), git. For the dashboard: [Bun](https://bun.sh). A team key
for the arena, an Anthropic API key, a Supabase project.

### Environment (`starter-kit/.env`, never committed)

| Variable | Purpose |
|---|---|
| `ARENA_URL` | arena base URL |
| `ARENA_API_KEY` | team key |
| `ARENA_DATA` | optional: path to the data package (default `data/package`) |
| `ANTHROPIC_API_KEY` | Claude |
| `LLM_MODEL`, `LLM_EFFORT` | optional: default `claude-opus-5-5`, `low` |
| `SUPABASE_URL` | audit database |
| `SUPABASE_SERVICE_ROLE_KEY` | runner write path (server side only) |
| `SUPABASE_ANON_KEY` | optional: `db_check` verifies anonymous read access |

### Setup

```bash
cd starter-kit
cp .env.example .env               # fill in the values above
uv sync --all-extras
uv run arena data                  # data package + Sunday release (after Sun 08:00)
uv run arena me                    # the key works
```

Database: run `db/migrations/001_init.sql`, `002_case_overview.sql` and `003_agent_telemetry.sql` in the
Supabase SQL editor (in order; each is safe to re-run), then:

```bash
uv run python -m hollerau.db_check        # write, read back, reject a duplicate move, clean up
uv run python -m hollerau.sync_suppliers  # supplier master for the dashboard
```

### Play

```bash
# free: the local simulator (scripted suppliers)
uv run arena-sim serve --data data/package          # in a second terminal
uv run python -m hollerau.run --set sim -v

# practice (costs quota and Claude credits)
uv run python -m hollerau.run --set practice --cases case:P02,case:P07 --parallel 5 -v

# the Live Final - start before 13:30 and leave it running
uv run python -m hollerau.run --set final --parallel 10 > data/final.log 2>&1
```

The runner waits for wave 1, plays each wave's cases in parallel within the wave cap and stops after
the fifth wave. Options: `--cases`, `--agent hollerau|naive`, `--waves`, `-v`.

### Diagnose and calibrate

```bash
uv run python -m hollerau.diagnose     # our cost maths vs every scored practice deal
uv run python -m hollerau.calibrate    # refit supplier-floor ratios -> config/calibration.json
```

### Dashboard

```bash
bash scripts/sync-dashboard.sh         # pull Lovable, check the types contract, test, build
```

Schema changes go in a new `db/migrations/NNN_*.sql` plus a prompt in `docs/lovable/` that makes the
dashboard match; `db/types.ts` must stay byte-identical to the dashboard's copy.

---

## Configuration switches

Strategy is configuration, not code: `starter-kit/hollerau/config/strategy.json`. Every mechanism above
can be switched off for an experiment without removing it:

| Key | What it does |
|---|---|
| `claims.enabled` | one checked claim per offer (off: Claude cites from the evidence list) |
| `concession_path` | minimum step per round, reciprocity threshold |
| `rule_accept.on_agreed / on_target / on_final_offer` | Python's own accepts (keep `on_final_offer` on) |
| `mindset_inference.enabled` | the inferred supplier mindset and everything that uses it |
| `owner_payment` | short payment for owner-run and cash-short suppliers |
| `capacity_respect` | never ask a shorter lead time in capacity cases |
| `swaps` | the trade engine (premium, default asks, wording that signals a want) |
| `concession_guard`, `floor_pacing`, `segments`, `cultures` | pacing, anchors and tone per protocol |

---

## Tests and quality gates

```bash
cd starter-kit
uv run pytest -q                          # 88 tests: cost maths, claims vs the arena's rules,
                                          # pacing, gates, schema, simulator, recorder
uv run ruff check && uv run ruff format --check hollerau tests
uv run --with mypy mypy --strict hollerau
```

The tests run on real fixtures: the practice case files, recorded supplier threads and the data
package. Claude is replaced by a stand-in client, so they cost nothing. Every claim kind is checked
against the arena's citation rules and against `facts.json`.

House rules: all money maths through the arena's cost function, never in model text; the audit write
comes before every send; strict types; timeouts on all I/O; one change, one test, one tagged restore
point (`git tag` lists every state, from `pre-v3` to `post-crash-finish`).

---

## What we learned (including what did not work)

From the agent's own replays, the EHL final's top three, and live A/B checks on the practice cases:

- **Evidence must be checkable, one piece at a time.** Unverifiable claims ("send us the data") cost
  trust; one verified claim per round beats a bundle.
- **Movement buys movement.** Holding the price flat ends the negotiation early; going backwards ends
  it outright (a supplier walked when our counter dropped from 4.97 to 4.81).
- **Final offers are final.** Pushing past them made suppliers walk in practice run 1 and again in a
  deliberate test (0.44 vs 2.91 on five cases).
- **Total cost, not unit price.** Payment days, freight terms and effective dates move the score as much
  as the price.
- **Tried and dropped:** bluffing about competitors (suppliers demand proof and do not fold),
  equal-cost alternative packages (scored lower live), aggressive anchoring by leverage position
  (neutral), and trading quality terms in quality-first cases (the cost function makes strict quality
  the best package).

More: `docs/winners_analysis/` (the EHL final's top three vs our replays) and `HANDOFF.md` (state and
open items).

---

## Repository layout

```
starter-kit/
  hollerau/                our agent
    negotiator.py            the turn: rules, Claude, gates, claims, pacing
    envelope.py              cost envelope, targets, lever packages (via arena_kit.cost)
    claims.py                checked claims from facts.json and the case file
    evidence.py              data-backed context for the prompt (indices, news, release)
    swaps.py                 priced trades
    telemetry.py             concession velocity, mindset, claim verdicts
    recorder.py              write-first audit (RecordingTable)
    run.py                   headless runner: sim / practice / final
    profiles.py, config/     strategy, protocols, calibration
    package.py, kit.py       typed access to the data package and the kit
    diagnose.py, calibrate.py, db_check.py, sync_suppliers.py, baseline.py, sample.py
  arena_kit/               Tacto's kit (unchanged): client, play loop, cost function, simulator
  tests/                   pytest suite
dashboard/                 Lovable dashboard (git subtree)
db/                        Supabase migrations + the shared types contract
docs/                      winners analysis, Lovable prompts
brief/                     Tacto's brief, API docs, submission rules
data/                      Tacto's data package (CC BY 4.0)
scripts/sync-dashboard.sh  dashboard sync + checks
HANDOFF.md                 current state, restore points, open items
```

---

## Credits and licence

Built by **team 42Planets** for the Tacto challenge of the Industrial Agents Hackathon 2026, with
[Claude](https://www.anthropic.com/claude) as the negotiator's language model.

Built on Tacto's [negotiation-arena-kit](https://github.com/tacto-playground/negotiation-arena-kit):
the arena, the kit (`starter-kit/arena_kit/`, MIT) and the data package, brief and documentation
(CC BY 4.0) are © 2026 Tacto Technology GmbH - see [LICENSE](LICENSE) and [LICENSE-data](LICENSE-data).
Our code in `starter-kit/hollerau/`, `db/`, `scripts/` and `docs/` is released under the same MIT
licence.
