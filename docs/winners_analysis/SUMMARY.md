# Tacto Arena Final - why the top 3 won

Source: https://arena-ehl2026-536919411157.europe-west3.run.app/results (data from `/v1/results`, `/v1/results/<team>`, and the `/replay/<id>` pages).
Analysed on 2026-10-25: all 30 final replays for each of the top 3 teams, compared against NoIdea (#4), Helllo World (#6) and TakeTheMoneyAndRun (#12).
Detailed notes per team: `notes_sellm.md`, `notes_coda.md`, `notes_fake.md`.

## Standings (5 waves, 30 cases, each wave scored 0-100)

| # | Team | W1 | W2 | W3 | W4 | W5 | Total |
|---|---|---|---|---|---|---|---|
| 1 | sellm | 78.0 | 58.8 | 73.6 | 70.7 | 70.5 | 351.6 |
| 2 | Codacabana | 83.6 | 57.9 | 64.3 | 65.2 | 76.0 | 347.0 |
| 3 | Fake It Till You Make It | 76.3 | 53.9 | 68.8 | 71.3 | 71.2 | 341.5 |
| 4 | NoIdea | 77.4 | 56.4 | 62.5 | 67.1 | 74.7 | 338.1 |
| 12 | TakeTheMoneyAndRun | 68.3 | 16.2 | 61.7 | 61.3 | 62.3 | 269.8 |

The waves were: W1 "Opening: close a fair deal", W2 "Read the supplier", W3 "Twins", W4 "New faces", W5 "Sunday's news".
42Planets does not appear in the final results (`/v1/results/42Planets` returns 404).

## How scoring works (as shown in the Result block of each replay)

score = (total cost of the best opening offer - total cost of the outcome) / (opening - best achievable)

- **It measures total cost, not unit price.** Payment days, incoterm, effective date, contract length and lead time are all priced in.
- **H03 shows this.** Helllo got the unit price cut from 85.00 to 84.14 and still scored **0**. The supplier quietly moved payment from 90 to 14 days, and the deal stayed FCA rather than DAP, so total cost rose above the opening. Coda scored 0.97 on the same case with DAP.
- **A no-deal walk-away can score 100.** In H07 every team walked away and every team scored 100.

## What separates the top 3 from everyone else (common to all three)

1. **No disasters.** None of the top 3 has a 0 or a timeout, and their lowest case scores are about 0.24-0.34. The field mostly lost in Wave 2: TMAR has four timeouts at 0, Helllo has 0 on H03, NightHunter 0.25 on H03. Consistency beats peaks: the gap between sellm and NoIdea is only 13 points over 30 cases.
2. **Total-cost-aware terms set in round 1 and restated in every message:**
   - payment days chosen to fit the supplier: 10-14 days for cash-hungry owner-run firms (the supplier pays for it in price), 90 days for corporates;
   - DAP for overseas suppliers;
   - effective date pushed to **2027-04-01** on price increases;
   - 24-36 month terms and "binding volume, our full demand" phrasing.
3. **Every claim is verifiable.** Out of about 330 claims across the top 3, 1 was contradicted (a sellm thousands-separator bug). Each number in a message sits next to its source ID.
4. **Disciplined closing:**
   - concessions shrink every round and they never split the difference;
   - they accept a `[final_offer]` if it beats the fallback, or once the gap is under about 0.2-1%;
   - they walk away when the price is above a verified alternative (H07).

## Signature edge of each team

### #1 sellm - "one claim per round"
- **Exactly one verified claim per message**, never more: 105 single-claim messages and zero with two or more. The order is fixed: index_change, then notice_period or should_cost, price_history, volume_change, delivery_record.
- Measured over all 180 replays, suppliers concede per message, not per claim:

  | Claims in the buyer message | Average supplier concession |
  |---|---|
  | 0 | ~0.3-0.7% |
  | 1 (sellm) | ~2.3% |
  | 2-3 (Coda) | ~5% |

  Bundling has diminishing returns, so spreading the same facts over rounds gets more total movement. H29: sellm got -17, -20, -22, -8 and -2.5 over five rounds and scored 99.7. Coda bundled three claims, got -34 once and then about -1 per round, and scored 66.8.
- **The deepest anchors on price increases:** a median of about 87% of the supplier's opening, as low as 73% (H29) and 75% (H38).
- **Effective date 2027-04-01 on every price increase:**
  - H26: a higher unit price than Coda, but a lower total cost, so sellm scored 67.7 to Coda's 52.9;
  - H21: sellm gave the date up and lost about 23 points against Coda at the same price.
- Short (~57 words), fully templated messages with no free text.
- Edge by case type: price increases average 76.5 vs 67-71 for the other top teams.
- **Weak spots:**
  - renewals: anchors too shallow, so the supplier accepted sellm's own first number (H30, H34);
  - capacity: insisting on a 28-day lead time triggered an overtime premium (H15, 55.3 vs Coda 88.5);
  - RFQs: never sent rival quotes to the cheapest bidder;
  - H04: refused the copper index clause.

### #2 Codacabana - "terms that fit the supplier"
- **Best choice of non-price terms:**
  - DAP on H03 (0.97);
  - kept 2027-04 on H21 (0.69);
  - switches a term as soon as the supplier prices it, e.g. H24 "if we stick to 30 days... 17.90" → took 17.80.
- **Does not fight capacity limits:** proposes the supplier's standard lead time (H15 0.89 vs sellm 0.55; H17 0.97).
- The anchor is close to the true floor (H27 opened at 223.48 against a best of about 223.62). Steps close about 21-30% of the gap, with only a token move after a big supplier concession.
- **Bundles 2-3 claims in round 1:** first concessions of -5 to -16%, then the supplier stalls.
- **RFQ:** negotiates all bidders in parallel and uses the cheapest live offer as a verified rival quote. It answers the losing bidder's final offer with "reviewing internally, how long is it valid?" rather than accepting (H09 0.62, best of all).
- Messages: template plus one LLM paragraph that mirrors the supplier's concerns (~146 words).
- **Weak spots:**
  - H04: refused the index clause, 49.6 vs TMAR 79.1;
  - H34: shallow renewal anchor;
  - H29: front-loaded claims;
  - H38: proposed a 3% deadband itself.

### #3 Fake It Till You Make It - "picking the most favourable verified data"
- **It does not actually bluff:** 0 contradicted claims. The "fake" is choosing the most favourable data window, e.g. PPI-D351 2025-11→2026-04 = **-12.0%**, where others cite -6.1% or -3.7%. It used that window 13 times, including on unrelated parts.
  - Caveat: TMAR (#12) used the same window 15 times, so this alone does not win.
- **Gives up terms the cost model barely values to get a lower price:**
  - H19: looser ppm plus a chargeback bought 614.85 vs sellm's 642.85 (0.55 vs 0.34);
  - H17: accepted a longer lead time.
- **Payment and contract terms set by supplier type:** short payment for owner-run firms; 24 months by default, with 36 kept as something to trade. Against owner-run suppliers this got lower prices than sellm's 36-month opening (H06, H12, H30, H34).
- **Option A/B/C packages in 21 of 30 cases**, which make suppliers show what they value.
- **Front-loads 2-3 claims in round 1:** a 3-claim message got about a 9-10% concession.
- **Weak spots:**
  - accepts too early: H28 at a 0.6% gap while the supplier was still moving, H13 a round-1 final offer;
  - counterproductive rival quotes (H26);
  - gave up the effective-date deferral (H21);
  - soft anchor on H38;
  - H07 refused the final offer by sending a package above the opening instead of walking away. It still scored 100, but that was risky.

## Levers that no top team used fully (where the next points were)

- **Accept a supplier-offered index clause with a deadband during a commodity spike.** On H04, TMAR and Helllo accepted copper 20% with a 5% deadband and scored about 0.78. All three top teams refused and scored 0.46-0.69.
- **Anchor deeper on renewals.** The supplier accepting your first number means you left money on the table (H30, H34).
- **Use the supplier's "Alternatively, with X: €Y" offers.** These are free information about how the supplier values its terms.
- **Combine the approaches:** sellm's one-claim-per-round pacing + Coda's term selection and capacity respect + Fake's trade-offs on low-value terms. None of the top 3 did all of it.

## Caveat
The per-team agent reports were spot-checked: claim distributions, the PPI-D351 windows, and the H03/H15/H21/H29 terms were all checked against the raw replays. Other per-case figures in the detailed notes come from those reports and were not all re-verified.
