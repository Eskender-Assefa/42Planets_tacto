# sellm (rank 1, 351.6) - why it scores high

Data: all 30 sellm replays parsed (term tables, claims, supplier deltas, results); deep reads H01, H07, H10, H13, H15, H17, H20, H21, H29, H32, H38, H11; contrasts against Coda/Fake/NoIdea/Helllo/TMAR on H04, H09, H10, H14, H15, H19, H21, H26-H29, H34, H38.

## Per-case scores (sellm vs others)
sellm: H01 82.4, H02 88.2, H03 92.1, H04 68.8, H06 78.2, H07 100, H09 50.8, H10 33.3, H11 69.4, H12 67.3, H13 34.4, H14 85.4, H15 55.3, H16 74.9, H17 91.5, H19 34.4, H20 72.9, H21 45.4, H24 73.3, H25 86.2, H26 67.7, H27 55.5, H28 91.6, H29 99.7, H30 39.9, H32 79.7, H34 48.8, H35 93.9, H37 81.0, H38 68.2.
No zeros (min 33.3). TMAR has five zeros, Helllo has one (H03).

Average by case type (sellm / Coda / Fake / NoIdea / Helllo / TMAR):
- price_increase (n=10): **76.5** / 71.3 / 67.6 / 67.8 / 60.5 / 48.9  <- the main edge
- renewal (7): 73.6 / 72.0 / 74.1 / 73.6 / 74.4 / 79.7
- raw_material (3): 66.5 / 59.8 / 63.9 / 73.6 / 55.1 / 43.2
- capacity (3): 73.9 / 86.9 / 74.5 / 79.0 / 73.3 / 79.6
- rfq (3): 55.0 / 59.2 / 56.8 / 46.0 / 53.0 / 24.5
- bundling (2): 68.3 / 69.8 / 73.1 / 66.4 / 64.5 / 43.5
- quality (2): 53.7 / 53.9 / 61.7 / 53.5 / 56.1 / 21.8

## 1. Opening move
- Anchor: 73-93% of the supplier's opening price (median about 87%). Deepest anchors: H29 307.80 vs 421.37 (73%), H38 2.73 vs 3.65 (75%), H13 77%, H07 79%. Shallowest: H15/H16/H34 93%, H02/H26/H35 93%. In RFQs (H09/H10) the first bid is about 85% of the *cheapest* quote (19.21 vs 22.50, 77.18 vs 94.50).
- Against an implied best price (deal price x best/outcome), the anchor is about 87-95% in price-increase cases (H29 87.5%, H01 87.7%, H04 87.8%, H17 88.7%, H02/H03/H14 about 95%). In renewals it often sits *above* the best price (H34 109%, H30 126%, H12 114%, H09 114%). That is the root of its weak renewals (section 6).
- The anchor looks computed by the model rather than a fixed percentage: different per case, 2-decimal "precise" numbers (166.44, 307.80, 569.24).
- Non-price terms are set in round 1 and then held:
  - payment_days: 90 in 16 cases, 14 in 9 (H01, H03, H10, H12, H15, H20, H28, H29; it even cut 90 -> 14 in H03), 10 in the three small-shop renewals (H06, H30, H34). This trades fast payment for price with cash-hungry owners. In H01 the supplier replied "Faster payment would help us more than anything ... for that we can do more on the price."
  - effective_date 2027-04-01 in every price-increase case where the date is negotiable (H01, H21, H26, H27, H28, H29). The supplier wanted 2026-12-01 or 2027-01-01. This defers the increase by 3-4 months and is a large hidden lever (see factor 2).
  - contract_months 36 in all renewals, bundling, capacity and raw-material cases plus the H37 RFQ (17 cases), sold with the line "We can commit for the longer term, which gives you planning security: 36 months." In H17 the deal price was 787.94, essentially the opening price of 786.70, yet the score is 91.5, so the 36-month lock carries almost all the value.
  - volume: stated (often at the current level, 20,000 in H12 bundling). In capacity case H15 it asked 12,300 against a cap of 8,610.
  - index_clause: "a fixed price without an index clause" by default (H04, H13, H14, H38). It proposed its own index clause only in H32 (PPI-C2431, 80% share, deadband 0, base 2026-08). The supplier then dropped 136.40 -> 117.30 (-14%) in one step, and the score was 79.7.
  - quality cases: ppm_commitment 300, chargeback 0 (H19, H20).
  - lead_time: asked 28 in H15 and 56 in H17, adopting the supplier's 84 from round 2.

## 2. Concession pattern
- The buyer rises monotonically, starting at about 20% of the gap and then larger shares as the gap shrinks. H29: +20.95, +13.67, +8.09, +0.86. H17: +21.46, +24.86, +39.78, +7.95. H04: +21.04, +25.74. Final steps are tiny (H25: +0.17, +0.03, +0.01; H38: +0.02, +0.01).
- It never matches the supplier's number itself. It accepts when the supplier is within about 0.5%: H03 80.20 vs own 79.83, H28 363.50 vs 362.03, H29 352.00 vs 351.37, H19, H27, H32. Otherwise it keeps sending small raises until a [final_offer].
- [final_offer]: always accepted unless the price is above its walk-away. Examples: H15 accepted at 28.40 against its own 25.89 (9.7% gap), H04 656.16 vs 616.02, H13 4.18 vs 3.78. If several suppliers are open it sends the holding text "We are taking it through our internal approval and will confirm shortly. There are no further changes from our side." and then accepts (H10, H37).
- Walk-away: only H07. The supplier held 1,920.78 against last purchase orders of 1,581.52/1,608.32 and a should-cost of about 1,567.90. The buyer walked after the final_offer. Every team walked in H07 and every team scored 100, so it does not differentiate.
- [agreed] at its own number happened four times (H06, H09, H12, H34). Each time sellm's bid was already above the supplier's floor (see section 6).
- Rounds: 2-7 buyer messages (130 messages across 30 cases). It plays out claims across rounds instead of closing fast.

## 3. Evidence / claims
- **Exactly one claim per message, never more** (105 claims in 130 messages, 0 messages with more than 1). Coda, Helllo, TMAR and NoIdea typically bundle 2-3 claims in round 1.
- Fixed priority order: index_change (falling index) -> notice_period (letter shorter than the 90 days in the contract) or should_cost -> price_history -> volume_change -> delivery_record -> quality_record -> news.
- Type counts: index_change 27, volume_change 21, delivery_record 17, should_cost 12, price_history 9, rival_quote 7 (RFQ only), quality_record 7, notice_period 4, news 1.
- Index picks: PPI-D351 2025-11 -> 2026-08 (-6.1%) or 2025-08 -> 2026-08 (-3.7%), AS-14404 -5.5%, PPI-C2431 -2.3%. These are often not the drivers the supplier cites (H01 supplier: LCI-C, PPI-C241). TMAR/NoIdea cherry-picked wider windows (-12%, -17.1%), also verified.
- Verification: 98 supplier turns contained a verified claim, 1 was contradicted, 6 returned "duplicate" (quality_record qn:... after an earlier sc record: H11, H20, H25, H26, H27, H35).
  - Only contradiction, H07: the text says "EUR 1,567.90" but the JSON says {"unit_cost": 1.567}, a thousands-separator parse bug. The supplier answered "The should cost figures you cite do not match the records. That costs trust."
- Supplier reaction: the average supplier concession is 2.49% of the previous price after a verified claim, versus 0.27% after a message without a claim and 0.20% after a duplicate. Other teams get bigger single drops (Coda 3.08%, TMAR 3.50%) but fewer of them (74/51 claim-bearing turns versus sellm's 98). Drip-feeding claims buys a separate concession per claim.
  - H29 one-per-round: -16.87 (index), -20.00 (notice 51 days), -22.00 (should-cost), -8.00 (volume), -2.50 (OTD). Total -69.37, deal at 352.00, score 99.7.
  - Coda H29 three claims at once: -33.87, then -1, -1.5, -1. Deal at 384.00, score 66.8. Helllo 377.37 (79.0), TMAR 398.50 (42.3).
- Some evidence is off-target but still verified: price_history in bundling H11 cites a single bearing at 6.93/7.21 against a bundle price of 38; H13 cites rising POs 3.83 -> 4.05. The news claim in H17 ("semiconductor supply back to normal") was verified but brought no concession.

## 4. Message style
- Fully deterministic templates (no LLM free text), average 57 words per message (max 95). Coda averages 146, Helllo 100, TMAR 207.
- Skeleton: "Dear <name>, thank you for your offer and for the reliable cooperation. We would like to settle this in a way that works for both sides. [one evidence sentence with refs]. On that basis we propose EUR X per unit, payment N days net, valid from ..." Later rounds use "thank you for your reply and for moving towards us. [evidence]. We can improve our proposal to EUR X ... Could you meet us there?" Sign-off: "Purchasing, Hollerau Pumpenwerke".
- Evidence sentences are canned per claim type: "Your letter doc:... gives us 81 days of notice, while our agreement ctr:... requires 90 days." / "Our bottom-up estimate of the full cost is EUR ... before margin (cost:...)" / "Your rolling twelve-month on-time delivery in 2026Q3 was 85.2 % (sc:...)" / "We hold a competing offer at EUR 21.00 per unit (offer:70270-1)".
- Tone: polite, cooperative, no threats and no walk-away bluffs. Every term is restated in full in each message, so there is no ambiguity for the supplier's parser.

## 5. Special cases
- **RFQ (H09, H10, H37)**: talks to every bidder in parallel. It sends normal claims to the cheapest supplier and rival_quote claims (the cheapest supplier's latest offer id, e.g. offer:70330-2 at 89.0) to the others. That pulled big drops from the expensive bidders (H10 70360: -13.50, -12.00), but those were never turned back on the cheapest bidder (no rival_quote sent to 70330). It ends up with the lowest bidder.
  - H10 33.3 (deal 87.00; Fake reached 84.00).
  - H09 50.8: switched payment to 90 then 45, and 70270 "agreed" at sellm's own 19.68. Coda kept 14 days and reached 18.90 (61.8).
  - H37 81.0, about the same as other teams.
- **Bundling (H11, H12)**: no bundle-specific tactic. It uses the same claim drip with 36 months and 90 days (H11) or 14 days (H12), volume 20,000. Scores 69.4 and 67.3, mid-pack.
- **Capacity (H15, H16, H17)**: 36-month lock and lead-time asks.
  - H15 failure: it demanded 28-day lead time plus volume 12,300. The supplier raised the price +2.20 ("With overtime we can deliver in 28 days, at a premium") and offered "Alternatively, with Lieferzeit 44 days: €26.20". sellm ignored the alternative, kept 28 days and accepted a 28.40 final. Coda kept 35 days and reached 26.30 (88.5 vs 55.3).
- **Raw material / index (H13, H14, H32, H38)**:
  - Default stance is a fixed price without an index clause. H14: kept 90 days and a fixed price, 34.70, 85.4 (Coda moved to 60 days, 35.20, 65.8).
  - H38: insisted on a fixed price while the supplier kept an index clause, then accepted the final at 2.92 with the clause (68.2; Coda 3.14 at 47.0; Helllo 40.2).
  - H32: its own index proposal got -14% at once.
  - H13: the supplier introduced AS-14301 45%, sellm adopted it and accepted the round-2 final at 4.18 (34.4).
  - H04 (copper): refusing the clause cost it. TMAR accepted a CU-NOTATION 20%, 5% deadband clause, reached 634.04 and scored 79.1, versus sellm's 656.16 and 68.8.
- **Quality (H19, H20)**: demands ppm 300 with 0 chargeback and cites OTD and quality records.
  - H20 72.9 is fine.
  - H19 34.4: the tight ppm demand kept the price high (642.85). Fake accepted ppm 2,500 with a EUR 150 chargeback and reached 614.85 (55.3).
- **Walk-away (H07)**: walked after a final_offer above its limit. Correct (100), but not unique.

## 6. Weakest cases
1. **H10 (33.3) / H09 (50.8) RFQ**: never used rival pressure on the cheapest bidder. In H09 it changed payment terms mid-stream (90 -> 14 -> 45) and lifted its bid into the supplier's floor ([agreed] at 19.68).
2. **H13 (34.4)**: accepted the round-2 final_offer (4.18 vs its 3.78) after only 2 claims, conceded an index clause, and used rising price history as "evidence".
3. **H19 (34.4)**: insisted on ppm 300 / 0 chargeback instead of trading quality terms for price.
4. **H30 (39.9), H34 (48.8), H06 (78.2), H12 (67.3) renewals with a shallow anchor**: it opened at 82-93% of the supplier price, which was already above the best achievable price. Its second step brought it level with the supplier's floor, and the supplier immediately [agreed] or sent a final.
   - H34: open 24.64 -> 24.69, [agreed]; TMAR opened 21.06 and closed at 23.50 (80.8 vs 48.8).
   - Only 2 claims were used before closing (H30, H34).
5. **H21 (45.4)**: opened with 90 days plus an April effective date. The family foundry raised the price +1.94 and asked for "45 days and a January start". sellm gave up **both**, including the valuable April date. Coda got the same 37.50 at 45 days but kept April and scored 68.7; NoIdea kept 14 days plus April, 37.00, 72.4.
6. **H15 (55.3)**: lead-time over-ask and ignored the supplier's "Alternatively" price (see section 5).
7. **H27 (55.5) / H26 (67.7)**: the supplier barely moved. sellm still beat Coda thanks to the April date.

## 7. Ranked factors behind the high score
1. **One verified claim per message, drip-fed in a fixed strength order.** Each claim triggers its own supplier concession (avg -2.49% per verified claim versus -0.27% without). It has the most claim-triggered concessions of any top team (98). Example: H29 five rounds, -69 total, 99.7, versus Coda's three-claims-at-once 66.8.
2. **Deferring effective_date to 2027-04-01 in price-increase cases.** H26: sellm's price 263.45 is *higher* than Coda's 257.89, yet total cost is lower (1,520,352 vs 1,522,812) and the score higher (67.7 vs 52.9). H28 and H29 do the same. Losing it in H21 cost about 23 points against Coda. This drives the best price-increase average of any team (76.5 vs 71.3).
3. **Deep, evidence-justified anchors in price increases (73-88% of the opening), plus slow and shrinking concessions.** It never closes the gap itself and accepts only within about 0.5% or on a final_offer (H03, H28, H29, H01).
4. **Packaging non-price value: 36-month contracts, payment days and fixed price.** 36 months are offered in 17 cases; the H17 score of 91.5 comes with essentially no price cut. Payment days are traded per supplier type: 14 days for cash-hungry owners (H01, H03, H28, H29), 90 days elsewhere (H14 kept 90 days and beat Coda's 60 by about 20 points).
5. **Zero-risk robustness.** It is fully templated: no zeros, no broken must-haves, no hallucinated numbers, and only 1 contradicted claim (a number-format bug) in 105. TMAR (5 zeros) and Helllo (H03 = 0) lost far more on blow-ups than sellm lost on its weak cases.
6. **Short, complete, parseable messages** (57 words, every term restated). Suppliers reply with term tables that mirror its terms and rarely add surprise terms.
7. **Correct walk-away discipline and RFQ coverage.** It walks only when the final offer exceeds its limit (H07 = 100). In RFQs it talks to every bidder with rival quotes and picks the cheapest; this keeps RFQ scores at par (55.0) even though the tactic is not optimal.

Biggest remaining upside: deeper renewal anchors, keeping the effective_date when pushed (H21), reading supplier "Alternatively" offers (H15), using rival quotes on the cheapest RFQ bidder, accepting deadbanded index clauses in commodity spikes (H04), and fixing the thousands-separator bug.
