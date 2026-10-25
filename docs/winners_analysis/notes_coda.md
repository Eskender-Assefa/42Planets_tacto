# Codacabana (Coda) – why it scores high (rank 2, 347.0)

Data: /tmp/arena_results/txt/Coda_*.txt (all 30 read via extracted trajectories; deep-read H03, H06, H07, H09, H13, H14, H15, H17, H19, H21, H24, H32, H34, plus openings of H11/H19). Contrasted against sellm, Helllo, TMAR, Fake, NoIdea on the same case.
Helper scripts (read-only analysis): /tmp/coda_scripts/{summ,traj,anchor,claims,steps}.js

## 0. Scoreboard (sum of 30 case scores)
sellm 2110.2 | Coda 2082.0 | Fake 2049.8 | NoIdea 2028.6 | Helllo 1911.6 | TMAR 1618.7

Coda never scored 0 on any case (min 31.6, H13). Helllo had a 0 (H03); TMAR had 4 timeouts at 0 (H09, H10, H13, H24) plus 3.9 on H20.
Coda's floor is the highest of all teams: the 7 lowest scores are 31.6 (H13), 34.8 (H10), 39.2 (H19), 45.7 (H30), 47.0 (H38), 48.6 (H27), 49.6 (H04).

Coda vs sellm per case (Coda − sellm):
- Coda wins: H15 +33.2, H21 +23.3, H09 +11.0, H17 +5.9, H34 +5.9, H30 +5.8, H19 +4.8, H03 +4.5, H01 +3.0, H12 +2.9, H32 +2.3, H10 +1.5, H06 +1.1
- Coda loses: H29 −32.9, H38 −21.2, H14 −19.6, H04 −19.2, H26 −14.8, H28 −8.4, H27 −6.9, H20 −4.4, H25 −3.1, H13 −2.8

## 1. Opening move

Template for round 1 (every case):
"Thank you for your offer and for the time your team has put into it." + 1 paragraph (either the fixed sentence "We value our cooperation and we understand the cost pressure on your side; we want an agreement that keeps our partnership healthy for both of us." or an LLM-written paragraph that reacts to the supplier's letter) + "We confirm a binding volume of N units a year for the M-month term, our full demand for this part, all placed with you." + one sentence per claim, each with IDs in brackets + "On this basis we propose: EUR X per unit, <all terms>..." + often "What would you need from us to move further on the price? We are open to discussing any term that helps you."

**Anchor level.** The opening price averages 85.9% of the supplier's opening price (median 90.4%). sellm averages 84.2% (median 86.6%).
- Coda's anchor sits very close to the best achievable price. Implied best price ≈ final × best/outcome (approximate). Examples: H38 opens at 2.66 vs ~2.66; H27 223.48 vs ~223.62; H15 25.98 vs ~26.13; H20 10.30 vs ~10.39; H28 357.19 vs ~359.88; H10 72.60 vs ~73.33; H35 13.85 vs ~14.01.
- So it anchors "at the floor", not below it. The range is 73–97% of the supplier's open. It is deep where evidence supports it (H38 72.9%, H06 77.1%, H09 77.7%, H30 77.3%) and shallow where it does not (H15 96.6%, H25 96.1%, H35 96.2%, H16 95.5%).
- sellm anchors much deeper on some price increases: H29 at 73% (vs Coda 90.4%), H04 at 85% (vs 90.7%), H17 at 87% (vs 95%).

**Non-price terms set in round 1.** All terms are set at once and are chosen per supplier/case, apparently to minimise total cost:
- payment_days varies by supplier: 10 (H06, H30, H34: owner shops that say "faster payment would help us more than anything"), 14 (H01, H03, H09, H10, H15, H20, H28, H29), 60 (H13, H38) and 90 (H02, H04, H07, H11, H14, H21, H24, H25, H26, H27, H32, H35, H37). Short payment is offered where the supplier values cash and the buyer pays little for it. Early pay buys price: H06 "the higher volume and especially the 10 days payment help us out, so I am dropping the price to 31.00" (−3.00, −8.8%).
- incoterm: DAP in H03. This was decisive. Same supplier, H03 outcomes:

  | Team | Price | Incoterm / payment | Score |
  |---|---|---|---|
  | Coda | 83.30 | DAP / 14d | 96.6 |
  | Fake | 83.70 | DAP | 91.9 |
  | TMAR | 83.58 | EXW / 45d | 18.1 |
  | Helllo | 84.14 | FCA | 0.0 |

- contract_months 36 on every renewal and bundling case, plus H13, H16, H17, H32, H37, H38 (planning security as currency).
- volume_per_year: always the "full demand" and restated every round. Raised to the forecast where it helps (H15: 12300 vs supplier's 8610).
- effective_date: delayed to 2027-04-01 in H21 and held after the supplier agreed ("I can do the 2027-04-01 start date"). This is the main source of H21 68.7 vs sellm 45.4: the final price was identical (37.50), but sellm reverted to 2027-01-01. Elsewhere Coda uses the notice-period date (2026-12-01/2027-01-01, H01, H24, H28, H29), where sellm pushes 2027-04-01.
- lead_time on capacity cases: Coda never pushes against the capacity constraint. It proposes the supplier's standard or longer: H15 lt 35 (standard), H17 lt 98 (supplier offered 94), H16 lt 35.
  - sellm asked lt 28 in H15. The supplier answered +2.20 ("Delivering in 28 days requires overtime"), final 28.40 vs Coda 26.30 (88.5 vs 55.3).
  - sellm asked lt 56 in H17. The price went up +1.75, final 787.94 vs Coda 772.85.
- ppm_commitment 300 + chargeback 0 on quality cases (H19, H20). Index clause: proposed where the supplier's cost is index-heavy (H32: PPI-C2431, 80%, deadband 0; H38: deadband 3%). Otherwise "fixed price" (index_clause None).

## 2. Concession pattern

- Buyer step size is deterministic: about 21% of the current gap (supplier's last price − own last price), sometimes about 30% (often when the supplier stalls). Examples:
  - H03: +1.01, +0.72, +0.52, +0.37, +0.25 (each 21% of the gap)
  - H27: +3.22, +2.30, +1.54, +1.04, +0.71, +0.47
- "Hold" rule: after a large supplier first concession (about 7% or more), Coda makes only a token move of 1–3% of the gap. Examples: H06 +0.05 after −8.8%; H12 +0.05 after −12.5%; H11 +0.06; H30 +0.01; H32 +0.22 after −13.9%; H09 +0.03.
- It never splits the difference. sellm's late steps go to 50–73% of the gap.
- Convergence is geometric, so the buyer never crosses the supplier. Typical length is 3–8 buyer messages (H09 and H37 had 11 incl. both suppliers). It never timed out.
- Acceptance rules:
  - (a) Always accepts a [final_offer] that beats its walk-away: 22 of 29 deals closed on final_offer.
  - (b) Accepts a non-final offer when the gap is below ~0.2% (H19 636.80 vs own 636.23; H28 365.50 vs 364.95; H29 384.00 vs 383.34).
  - (c) Accepts "[agreed]" when the supplier takes its number (H12 23.38, H34 24.45).
- Walk-away: H07. The supplier's final offer of 1920.78 was above the verified rival quote of 1491.83, so it walked: "Buyer [] walk_away round 5". Score 100 (the best outcome was no deal).
- Term adaptation: when the supplier prices a term against it, Coda drops that ask and moves to the supplier's stated trade.
  - H21: asked 90 days, price went up +0.44 ("90 days is just too long"). Next round 45 days; the supplier then gave −1.50.
  - H24: the supplier said "If we stick to 30 days payment, I can do 17.90". Coda switched to 30 days and even lowered its own price (−0.17); the supplier gave 17.80.
  - Also H14 (90→60) and H25 (90→60).
  - Downside: sometimes too accommodating. In H14 sellm kept 90 days and still got 34.70 vs Coda's 35.20.

## 3. Evidence / claims

- Totals: 135 claims, all verified. 0 contradicted, 0 duplicate (never re-cites the same fact). sellm had 1 contradicted (H07) and 6 duplicates; NoIdea had 10 duplicates.
- Types:

  | Type | Count |
  |---|---|
  | index_change | 29 |
  | price_history | 25 |
  | volume_change | 25 |
  | delivery_record | 25 |
  | should_cost | 14 |
  | rival_quote | 12 |
  | notice_period | 4 |
  | quality_record | 1 |

- Front-loaded: on average 2.74 claims in round 1 (mostly 3), 0.79 in round 2, 0.5 in round 3, 0.11 in round 4, then none. sellm drip-feeds exactly 1 claim per message for rounds 1–5.
- Also cites memo documents in prose without a Claim line, as soft levers:
  - "In our call of 2026-07-21 (doc:20260721-70340-M2) you offered to walk us through your calculation" (H24, H09)
  - "Your letter of 2026-07-27 (doc:...) says your material is covered at fixed prices" (H13)
- Supplier reactions:
  - Round-1 three-claim bundles bring large first concessions (% of opening): H30 −15.7, H32 −13.9, H38 −13.4, H12 −12.5, H09 −11.1, H13 −10.9, H06 −8.8, H29 −8.0, H24 −7.5, H11 −6.8, H28 −5.2, H01 −4.0.
  - Later single claims bring 0.3–2.3% (H01 price_history −4.50; H28 volume_change −6.00).
  - Rounds without claims bring 0–0.5%.
- Wasted claim type: price_history. All 25 Coda price_history citations got "it holds, but it does not change our calculation". sellm used it 5× and all 5 got "took it into account". Coda's index/volume/should_cost/notice claims mostly got "took it into account" (15/19, 20/22, 11/12, 4/4).
- Some evidence is chosen mechanically. H32 cites a rival quote of 138.64, higher than the supplier's own 136.40 (and mixes "per 100 units"). H14 cites a PPI-D351 fall the supplier is hedged on ("covered at fixed prices until December 2028").
- Weakness vs sellm: front-loading wastes the supplier's per-claim responsiveness. In H29 Coda got −33.87 in round 1 and then −1.00, −1.50, −1.00, accepting 384. sellm dripped one claim per round and got −16.87, −20.00, −22.00, −8.00, −2.50, ending at 352 (99.7 vs 66.8).

## 4. Message style

- Hybrid: a deterministic template skeleton plus one LLM-generated empathy/argument paragraph per message.
- Fixed lines:
  - "Dear Sir or Madam,"
  - "Thank you for your reply and for the step you have taken; we appreciate it."
  - "We confirm a binding volume of ..."
  - claim sentences like "Electricity producer prices changed -6.1% from 2025-11 to 2026-08 (idx:PPI-D351@2025-11, idx:PPI-D351@2026-08)."
  - "On this basis we propose: EUR X per unit, payment N days net, delivery DAP, for our full demand of N units a year over M months."
  - "Kind regards, Hollerau Pumpenwerke, Purchasing"
- The LLM paragraph mirrors the supplier's stated pain ("understand that extended payment terms put pressure on your business", "glad the thirty-day payment term helps your shop"), acknowledges the movement, restates full-volume commitment and rising forecast, and says "we are moving our proposal toward you again".
- Length: average 146 words per message (sellm 57, Fake 75, Helllo 100, NoIdea 137, TMAR 207). Tone is warm and cooperative, never threatening. It addresses the counterpart by name in later rounds ("Martin").
- Every message repeats the full term sheet, so the supplier never "forgets" a term.

## 5. Special cases

- **RFQ (H09 61.8, H10 34.8, H37 81.0):** negotiates all bidders in parallel.
  - Uses the cheapest bidder's live offer as a verified rival_quote against the others ("Another bidder offers EUR 20.00 per unit for this part (offer:70270-1)").
  - Keeps a low, slowly rising number with the cheapest bidder (H09: 17.49→18.79 over 7 rounds; final 18.90 vs sellm 19.68, who accepted "agreed" in round 3).
  - Answers a losing bidder's final_offer with a holding note ("thank you for your offer, which we are reviewing internally. Could you confirm how long it remains valid?") rather than accepting; 70260 then walked away.
  - Weak spot H10: accepted the cheapest bidder's final offer at round 3 (86.50) without citing rivals back at it. Fake kept going to 84.00 (47.1).
- **Bundling (H11 69.4, H12 70.2):** 36 months, full consolidated volume (15,000 and 20,000), payment chosen per supplier. Patient 21–30% steps over 7–8 rounds; H12 ended with the supplier "agreeing" to the buyer's 23.38.
- **Capacity (H15 88.5, H16 74.8, H17 97.4):** see §1. Does not fight the constrained resource; accepts the standard or a longer lead time and offers payment/term/volume instead. This is the main source of the H15 and H17 gains.
- **Quality (H19 39.2, H20 68.5):** demands ppm 300 with chargeback 0 (vs supplier 2200/8400 ppm). The supplier accepted ppm 300 immediately in both. H19 then ground down 683.82→636.80 over 8 rounds; Fake reached 55.3 on H19.
- **Raw material (H13 31.6, H14 65.8, H32 82.0):**
  - H32: proposed the index clause itself (PPI-C2431, 80% share, deadband 0) and got a −18.90 first move.
  - H13: insisted on "fixed price" while the supplier kept its AS-14301 index clause; the final contract has the clause anyway.
  - H38 (renewal with index): proposed deadband 3%; price stuck at 3.14. sellm accepted the supplier's 0% deadband clause at 2.92 (68.2 vs 47.0).
- **Walk-away (H07, 100):** walks on [final_offer] when it is worse than the verified BATNA (rival quote 1491.83). It does not chase, but it also does not walk early (5 rounds).

## 6. Weakest cases and why

| Case | Coda | Benchmark | Why Coda lost ground |
|---|---|---|---|
| H13 | 31.6 | NoIdea 41.6 | Only 2 rounds; accepted the final 4.18 with the index clause. NoIdea got 4.11 (24 months, 90 days). |
| H10 | 34.8 | Fake 47.1 | Accepted the cheapest bidder's final quickly; rival quotes used only on the expensive bidders. |
| H19 | 39.2 | Fake 55.3 | Anchor 601.76 (88%); 21% steps converged to the supplier's slow path. |
| H30 | 45.7 | Fake 51.6 | Opening at 77% met −15.7%; the "hold" step then triggered a final offer at round 2. |
| H38 | 47.0 | sellm 68.2 | Self-proposed 3% deadband and 60 days; the supplier priced the deadband. |
| H04 | 49.6 | TMAR 79.1, Helllo 77.7 | Rejected the supplier's CU-NOTATION index clause (5% deadband); others accepted it for about 632–634 vs Coda's 661.50. |
| H34 | 54.7 | TMAR 80.8 | Anchor 24.42 was too timid (only 0.08 below the supplier's first counter); the supplier "agreed" at 24.45 in round 2. TMAR opened at 21.06 and got 23.50. |
| H26 | 52.9 | sellm 67.7 | Effective date kept at 2027-01-01. sellm pushed 2027-04-01: higher price, but 3 months of old price. |
| H29 | 66.8 | sellm 99.7 | Front-loaded claims, moderate anchor (90%), and accepted a non-final 384 at round 4. sellm anchored at 73%, dripped claims, delayed the effective date, and ended at 352. |

Pattern: Coda loses when the best deal needs an aggressive anchor, accepting a supplier-offered structure (index clause), or a delayed effective date. It wins when the best deal needs the right non-price structure and patient, fair steps.

## 7. Ranked factors behind the high score

1. **Total-cost-aware choice of non-price terms, set in round 1 and repeated every message.** Examples: DAP in H03 (96.6 vs Helllo 0 / TMAR 18), 10–14-day payment for cash-hungry owners (H06, H30, H34), 36-month terms, full-volume commitment, delayed effective date where granted (H21 +23 vs sellm). This is the biggest differentiator against weak teams.
2. **Not fighting the capacity constraint.** It offers the supplier's standard or a longer lead time (H15 35d, H17 98d) instead of demanding faster delivery, which suppliers price as overtime. H15 88.5 vs sellm 55.3; H17 97.4 vs 91.5.
3. **Robustness: zero failures.** No timeouts, no zeros, no contradicted or duplicate claims (135/135 verified), a correct walk-away in H07, and holding replies to losing RFQ bidders. Lowest score 31.6, vs zeros for TMAR and Helllo.
4. **Calibrated anchor near the true floor** (about 99% of the implied best price on average) plus deterministic 21–30% gap-closing steps and a "hold" after big supplier moves. This produces reliable convergence near the best price without provoking final offers too early (H03, H17, H35, H02, H25 all 83–97).
5. **Strong round-1 evidence bundle** (typically index + volume/forecast + delivery/should-cost) plus memo-document citations. This produces large first concessions (−5 to −16% in 12 cases).
6. **Reading and adopting supplier-stated trades.** "If we stick to 30 days payment, I can do 17.90" became 30 days and 17.80 (H24). In H21, 90 became 45 days for −1.50. The supplier then keeps conceding.
7. **RFQ patience:** many small steps with the cheapest bidder while using its live offer as a rival quote against the others (H09 61.8 vs sellm 50.8).

**Versus sellm (which edged it by about 28 points over 30 cases):**
- sellm drip-feeds exactly one claim per round. Each verified claim keeps triggering a fresh concession (H29: −17, −20, −22, −8), where Coda gets one big round-1 move and then crumbs.
- sellm anchors deeper on price increases (H29 73%, H04 85%).
- sellm routinely pushes effective_date to 2027-04-01 (H01, H26, H28, H29).
- sellm holds 90-day payment when the supplier grumbles (H14) and accepts supplier-proposed index clauses (H38).
- sellm's messages are about 57 words vs Coda's about 146.
- Coda beats sellm where sellm over-asks on constrained terms (H15, H17 lead time), reverts a granted concession (H21 effective date), or closes early in an RFQ (H09).
