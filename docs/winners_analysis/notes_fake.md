# Fake It Till You Make It (rank 3, 341.5) - why it scores high

Source: all 30 replays in /tmp/arena_results/txt/Fake_*.txt, compared with sellm/Coda/NoIdea/Helllo/TMAR on the same cases.

## Scoreboard (Fake vs sellm)
Fake beats sellm by a lot on H19 55.3 vs 34.4, H10 47.1 vs 33.3, H30 51.6 vs 39.9, H34 59.7 vs 48.8, H06 87.6 vs 78.2, H12 74.4 vs 67.3, H32 84.7 vs 79.7, H17 97.5 vs 91.5, H11 71.8 vs 69.4.
Fake loses a lot on H04 45.5 vs 68.8 (TMAR 79.1), H26 44.5 vs 67.7, H38 46.1 vs 68.2, H28 74.6 vs 91.6, H13 23.9 vs 34.4 (NoIdea 41.6), H21 37.9 vs 45.4 (NoIdea 72.4, Coda 68.7), H15 51.2 (Coda 88.5), H09 42.2 (Coda 61.8), H01 74.1 vs 82.4.

## 0. The team name is not literal: no bluffing
- 90 claims in total, **89 verified, 1 duplicate (H11 volume_change), 0 contradicted**. There are no unverifiable numeric assertions. Every figure in a message has an ID next to it.
- The "faking" is **cherry-picking verified data**. The clearest case is the index window: Fake cites `idx:PPI-D351@2025-11 -> @2026-04 {"change_pct": -12.0}` 13 times. That is the trough window. Other teams cite the same series ending 2026-08: sellm uses 2025-08->2026-08 at -3.7% (10 times) and 2025-11->2026-08 at -6.1%; Coda uses 2025-11->2026-08 (16 times). Suppliers verify the claim ("it holds and we took it into account"), and Fake gets the effect of a 12% decline where others get 4-6%.
  - Fake cites PPI-D351 -12% even on parts where it is not obviously the relevant index (H10 RFQ, H20, H21, H24, H28, H29, H30, H34, H06, H19, H01, H03). It is still accepted.
- Weak spot: it also cites evidence that is unhelpful. In H26 it cites `rival_quote quote:7200076 {"unit_price": 258.51}` when the supplier's opening is 255.95, so the rival is higher. The supplier did not move. In H13 it cites a rival at 4.64 against an opening of 4.76, which puts a soft cap on concessions.

## 1. Opening move
- **Anchor**: median about 85% of the supplier's opening (range 59-98%). Measured against the best-achievable price (approximation: opening unit price x best_total/opening_total), the anchor is **about 1.0x the best-achievable price in most single-supplier cases**:
  - Close to 1.0x: H14 0.99, H19 1.00, H21 1.01, H25 1.00, H27 1.00, H28 0.99, H32 0.98, H13 0.98.
  - It looks computed from data, e.g. last PO price x index (H25: history 23.13, anchor 22.89; H14: 33.94 vs 33.58).
  - More aggressive: H24 (68.6%), H29 (77.7%), H09/H10 RFQs (59-65% of the dearest supplier).
  - Too timid in places: H38 85% (sellm 75%), H04 89%, H15 98%, H26 97%.
- **Non-price terms set in round 1, every case**:
  - **payment_days is chosen by supplier persona.** Owner-run suppliers get short terms: 14 days (H01, H03, H10, H12, H15, H20, H28, H29) or 10 days (H06, H30, H34). Corporate key-account suppliers get 90 days (H02, H04, H11, H13, H25, H26, H27, H32, H35, H37, H38). Owners value cash. Ilzauer, H12: "I like the 14 days payment, so I can agree to a 24-month contract if we settle at 25.00".
  - **contract_months 24 by default.** 36 is offered as "Option B" or conceded late (H02, H17, H25), never anchored. sellm anchors 36. On the same suppliers Fake got lower prices at 24 months: H06 29.50 vs sellm 30.07@36, H12 22.92 vs 23.69@36, H30 4.10 vs 4.30@36, H34 24.25 vs 24.69@36.
  - **effective_date 2027-04-01 on price increases** (H01, H21, H24, H26, H27, H28, H29). It uses the notice_period claim when the supplier's notice is short: H29 "Your letter gives 77 days' notice ... our contract requires 90 days".
  - **volume_per_year** restated where relevant (H06 8670, H12 20000 bundle, H38 90000).
  - **index_clause**: offered proactively in raw-material cases. H32 round 1 offers PPI-C2431 at 80% share with 0 deadband and the supplier answers -19.10 (-14%). H13 offers it as "Option B". H04 and H38 open with None, and that cost money (see section 6).
  - **lead_time** matched to the supplier's capability, or loosened as a trade: H10 35 days for 70330, H17 98 days.
  - **Quality case H19**: ppm 2500 (looser than the supplier's 2200) plus a chargeback of €500, 300 or 150 across three options. It concedes ppm, which barely counts, and buys price with it. sellm demanded ppm 300 and got 642.85 against Fake's 614.85.

## 2. Concession pattern
- Buyer steps follow a reciprocity / gap-split rule: each step is about 25-55% of the remaining gap, or about 0.75-0.9x the supplier's last move. Steps shrink geometrically.
  - H19: supplier -34.55/-14.44/-7.56/-5.77/-3.00/-2.50/-1.15; buyer +26.57/+11.69/+5.94/+4.05/+2.34/+1.43.
  - H29: supplier -35.37, buyer +32.17; supplier -12.50, buyer +6.81; supplier -4.00, buyer +1.29.
- When the supplier holds, it keeps making tiny steps (H02 +0.20/+0.15/+0.41/+0.29; H25 +0.10..+0.30; H26 +2..+4) and never jumps to the supplier's number.
- **Acceptance rules**:
  - Any [final_offer] is accepted immediately (H01, H02, H04, H06, H13, H15, H16, H17, H19, H21, H24, H27, H30, H35, H10, H37). The exception is H07.
  - Otherwise it accepts when the supplier is within about 1% of its own last bid: H03 83.70 vs 83.41, H28 373.00 vs 370.89, H29 368.00 vs 367.58, H32 113.80 vs 112.56.
  - It also accepts on "agreed" or at the round cap (H25, H26 accepted at round 5-7 without a final_offer).
- Rounds: median 3-4 buyer messages per supplier. It never presses past a final_offer.
- **No explicit walk_away in any case.** H07: the supplier sat at 1912.42 (essentially its 1927.94 opening) through rounds 1-4, then issued a final_offer. Fake did not accept. It sent a re-packaged offer "unit price EUR 1928.63, payment 90 days net, contract 12 months", which is above the opening. The supplier walked away (end_reason no_deal), and no-deal was the correct outcome (score 100). sellm got the same result by an explicit `walk_away` in round 3. Fake's route works but is risky: if the supplier had accepted that package, the deal would likely have broken the must-have.

## 3. Evidence / claims
- Claim types used: volume_change 27, index_change 24, delivery_record 12, rival_quote 10, price_history 6, should_cost 5, notice_period 3, news 3.
  - It never used quality_record (sellm used it 7 times).
- **It front-loads claims.** Round 1 has 1 claim in 17 negotiations, 2 in 12, 3 in 5. Later rounds have 0-1 claims and many have none. sellm always sends exactly 1 per round; Coda mostly 3 in round 1.
- **Supplier concession % per response, by number of verified claims in it** (all rounds pooled):
  - Fake: 0 claims 0.76% (n=67); 1 claim 2.23% (n=40); 2 claims 5.15% (n=17); 3 claims 10.51% (n=5).
  - sellm: 0 claims 0.27%; 1 claim 2.69%.
  - Round-1 average concession: Fake 4.9%, sellm 4.1%, Coda 6.1%.
- Examples of big responses to stacked claims:
  - H19: 3 claims (index -5.5, OTD 73.1%, volume +13.3%), supplier -34.55 (-5.1%).
  - H29: 3 claims (PPI -12, volume +12.5, notice 77 vs 90 days), supplier -35.37 (-8.4%). Owner reply: "You did your homework on the index and the volume, I respect that".
  - H06: 3 claims, supplier -3.50 (-10%).
  - H12: news claim "We read that you have spare capacity (news:20260514-12)" was enough to close; supplier "You are right about our free capacity, good catch", -2.08 to agreement.
- Claim ordering: index or volume first, then delivery_record or notice. should_cost and price_history are held for later rounds, which is a mistake (see H04).
- Supplier reactions (each counted once):
  - "took it into account": index_change 19/20, volume 19/23, delivery 7/9, rival 6/7, news 3/3, notice 3/3.
  - "does not change our calculation": **price_history 5/5**. History never moves a supplier.

## 4. Message style
- Hybrid. A deterministic engine produces the numbers and the evidence sentences; an LLM writes the relationship framing around them.
- Fixed evidence templates:
  - "The PPI-D351 index changed -12.0% from 2025-11 to 2026-04 (idx:...)"
  - "Our forecast for this part is up 13.3% (fc:...)"
  - "Your on-time delivery last quarter was 73.1% (sc:...)"
  - "Another bidder offers this part at EUR 94.50 per unit (offer:70330-0)"
  - "We hold a quote for this part at EUR..."
  - "Our recent orders of this part were at EUR..."
  - "Our should-cost estimate for this part is EUR..."
- **MESO packages**: "We could agree on any of these packages: Option A / Option B / Option C" appear in 21 of 30 cases. Options typically vary contract term (24/36), index clause, chargeback level, or lead time at near-identical price.
- Persona hooks from the brief, e.g. H29: "We value our long relationship and remember your support in keeping the old price during a difficult period".
- One information-seeking question per message: "Could you send us a cost breakdown for this part?" (15 times), plus "Which of the packages below works best for you?" (14 times).
- Late-round templates: "thank you for your reply - we appreciate the step you made", "We are close. One more step from your side and we can sign."
- Length: median 71 words (sellm 56, Helllo 98). Polite and cooperative, signed "Hollerau Pumpenwerke GmbH, Purchasing". It does not threaten.

## 5. Special cases
- **RFQ (H09, H10, H37)**: negotiates every bidder in parallel. The cheapest bidder's live offer is cited as a rival_quote against the dearer ones (offer:70330-0, then -1 as it falls). Each bidder gets different payment and lead-time terms. It rides the cheapest bidder longest:
  - H10: 70330 went 94.50 -> 84.00 over 5 rounds (sellm 87.00, Coda 86.50). Fake let lead time go to 35 for this bidder. 70360 walked, 70320 reached final at 109.50.
  - H37: 20.10 with the incumbent.
  - H09 weak: offered payment 90 to the owner bidder 70270, who stayed at 45; at agreement it accepted lead time 42 vs its own 35. Coda got 18.90 at 14 days, Fake 20.02.
- **Bundling (H11, H12)**:
  - H12: 2 rounds; anchor 21.54 (77%), 14 days, 24 months, 20000/yr; spare-capacity news; 22.92 agreed (74.4).
  - H11: 7 slow rounds to 33.80 (71.8). Its second volume_change claim was a duplicate.
- **Capacity (H15, H16, H17)**:
  - H17 is its best trade: in round 5 it offered lead time 98 (looser) and the supplier dropped -14.82 to 772.79 (97.5; sellm 787.94 at 84 days).
  - H15 weak: asked volume 12300 (above capacity) and lead time 28. The supplier refused and raised price +2.00, and Fake accepted 28.50 (above the 26.90 opening). Coda got 26.30 with 35-day lead time and 8610 volume.
- **Quality (H19, H20)**:
  - H19: trades ppm for a chargeback and price (see section 1).
  - H20: ppm 8400 -> 300 at 14 days, 11.11.
- **Raw-material index (H13, H14, H32, H38, H04)**:
  - H32: proactive index proposal, a big round-1 drop, 113.80 (84.7; sellm 116.10).
  - H14: accepted the supplier's 10% PPI clause, 34.79 (83.1).
  - H13: supplier issued a final_offer straight away in round 1 (4.33 with index and 60 days); Fake accepted at once. NoIdea pushed to 4.11.
- **Walk-away (H07)**: never accepts a final above its limit; ends no_deal. See section 2.

## 6. Weakest cases and why
1. **H04 45.5** (TMAR 79.1, Helllo 77.7):
   - Round 1 had only a volume_change claim, and the supplier went UP +0.32.
   - should_cost and price_history were held until round 3, by which time the supplier was at final_offer.
   - Index clause refused throughout. TMAR sent 3 claims in round 1 including should_cost and accepted the supplier's CU index clause: 634 vs Fake 662.53.
2. **H26 44.5** (sellm 67.7): it changed effective_date to 2027-04-01 plus 90 days, and the supplier repriced up +8.37 and never moved. It cited a rival quote above the opening. Final 264.32 is above the opening of 255.95; this is a narrow-range case.
3. **H38 46.1** (sellm 68.2): timid anchor (85% vs sellm 75%), 24 months not 36, and it flip-flopped the index clause (None -> accept -> None).
4. **H21 37.9** (Coda 68.7, NoIdea 72.4): it dropped the effective_date deferral (04-01 -> 01-01) in round 2 and oscillated payment 90/45/90/14. Same final price as Coda (37.50), but it lost the deferral value.
5. **H13 23.9**: accepted a round-1 final_offer. It also cited a weak rival quote (4.64), which anchored the supplier high.
6. **H28 74.6** (sellm 91.6): accepted at round 3 at a 0.6% gap while the supplier was still conceding about 2.5 per round. sellm kept adding one claim per round and closed at 363.50 vs 373.00. The cause is evidence exhaustion plus the early-accept threshold.
7. **H15 51.2**: over-asked capacity (see section 5).

## 7. Ranked factors behind the high score
1. **Cherry-picked but verifiable evidence windows.** The PPI-D351 trough window (-12.0%, 13 uses) gives 2-3x the leverage of the windows other teams cite, with 0 contradictions. This is the real "fake it": it never fabricates, and it chooses the window that tells the strongest story.
2. **Persona-aware non-price trades.** 10-14 day payment for owner suppliers and 90 days for corporates; 24-month contracts held back as currency (36 only as an option). These win better prices on the same suppliers than sellm's 36-month anchors (H06, H12, H30, H34).
3. **Conceding terms the cost model barely values to buy price.** Looser ppm in H19, longer lead time in H17 and H10, proactive index clauses in H32 and H13. These deliver its biggest outperformances (H19 +21, H17 +6, H32 +5, H10 +14 vs sellm).
4. **Front-loaded claim stacking.** 2-3 verified claims in round 1 produce supplier concessions of 5-10% in a single response (H19, H29, H06, H12, H32), before the supplier's resolve hardens.
5. **MESO option packages in 21 of 30 cases.** Suppliers pick a structure and often reveal what they value ("I like the 14 days payment ... if we settle at 25.00").
6. **Disciplined reciprocal concessions.** Steps shrink geometrically, it never jumps to the supplier's number, and it holds small increments against a stonewall. This gives near-best outcomes in grinding cases (H25 86.2, H02 88.2, H35 87.6, H17 97.5).
7. **Never accepts above its limit.** H07 no deal scores 100.
8. **Weaknesses that keep it below sellm**:
   - It accepts any final_offer at once (H13, H04).
   - The ~1% early-accept threshold, plus running out of claims after round 2, leaves money on the table (H28, H01). sellm drips one claim per round and keeps the supplier moving.
   - Index-clause refusals (H04, H38).
   - Self-harming evidence (H26, H13 rival quotes above or near the opening).
   - Persona mis-reads on payment (H09) and capacity over-asks (H15).

**Fake vs sellm in one line:** Fake hits harder early (stacked, cherry-picked claims and smart term trades) and closes fast. sellm is steadier: one claim per round, longer tails, and an explicit walk-away. Fake wins big on quality, RFQ and owner renewals, and loses on hard-line corporate price increases and index-clause cases.
