# 42Planets vs the winners' playbook

Data: our latest practice replay for each of the 10 cases, fetched read-only from arena.tacto.ai with GET requests (no new sessions).
- P02, P07, P08, P10, P18 = `post-ask` (the final candidate).
- The other 5 = the `post-guard` run.

They were compared against all 30 final replays of each of sellm, Codacabana and Fake It (see SUMMARY.md). The cases are different, but the playbook transfers. Several practice cases have close final twins:
- P01 Brandlhuber +9.5% ≈ H29 Brandlhuber +10% (same supplier, sup:70110);
- P02 Nordmark copper ≈ H04 Vesmo copper / H26 Nordmark;
- P10 capacity ≈ H15/H17.

No code was changed. These are notes only.

## Scoreboard of habits

| Habit | sellm | Coda | Fake | **42Planets** |
|---|---|---|---|---|
| Messages with a checked claim | 66% | 43% | 41% | **26%** |
| Claims verified | 98/105 | 135/135 | 89/90 | **6/18 (12 irrelevant)** |
| Index-change claims registered | 27 | 29 | 24 | **0** |
| Volume / delivery / price-history / notice claims | 51 | 79 | 48 | **0** |
| Supplier raised price after our 1st message | rare | rare | rare | **5 of 10 cases** |
| Opening anchor (median, vs supplier's opening) | 0.87 | 0.90 | 0.89 | **0.93** |
| Round of the supplier's first final_offer (avg) | 3.4 | 4.1 | 3.6 | **2.4** |
| Buyer messages per case | 4.3 | 4.8 | 4.4 | **3.3** |
| Zero scores | 0 | 0 | 0 | 0 (good) |

## Gap 1 - our evidence barely registers (biggest gap)

The winners get about 2.3% of supplier movement for every message carrying a new verified claim, and about 0.3% without one. Our evidence is mostly lost.

### a) Index claims never count: one ID instead of two
- The arena checks an index change only with **2 × `idx` IDs of one series** (brief/api.md, "What counts").
- `hollerau/evidence.py` builds sentences with both IDs, but the emails as sent cite only the end month:
  - P01: "Energy producer prices fell -3.7% from 2025-08 to 2026-08 (idx:PPI-D351@2026-08)"
  - P11: same index, same single ID
- Result: no `Claim index_change` was registered in any of our 10 replays. index_change is the winners' most-used claim (24-29 each). sellm opened H29 with exactly this claim against the same supplier and it was verified.

### b) 12 of 18 claims were "irrelevant" rival quotes
- **Citing the supplier's own offer back at it as a rival quote:**
  - offer:70610-0 / -1 (P07), offer:70410-0 (P10), offer:70740-0 (P18);
  - the rules only allow "another supplier's offer in this session".
- **Citing `quote:` IDs that are not this case's quote for this part:**
  - quote:7300001, 7300003, 7300004, 7300008, 7300011, 7200008, 7200019;
  - the arena answered "does not concern this part or our company".
- **The supplier's reply:** "Which figures is that based on? Please send us the data." That is the opposite of the "fair point" concessions the winners get.

### c) Claim types we never use
The winners rotate through these. Our brief either lacks them or the model drops them:

| Claim type | How to cite it | Notes |
|---|---|---|
| `volume_change` | `fc:<part>@<month>` with % | sellm and Fake use it a lot |
| `delivery_record` | `sc:` with on-time % | We cite sc rows, but our sentence mixes OTD and ppm, so the arena checks it as quality_record (ppm). sellm cites OTD 85.2% for the same sup:70110 as a delivery claim. |
| `price_history` | 2-8 × `po` of the same part | Used by Coda (25) and sellm (9). It verifies, but suppliers say "does not change our calculation", so its value is low. |
| `notice_period` | the letter `doc` + contract `ctr` | e.g. "51 days given vs 90 in contract". sellm used it in H01 and H29, the supplier said "a fair point" and made a big step down. |

### d) Pacing
- We put 2-3 claims in round 1 (P01, P18) and then mostly nothing: 32 of 43 buyer messages carry no claim.
- In P02 we sent 3 messages in a row with no new claim and a buyer move of +0.02 / 0 / +0.58. The supplier didn't move at all (374.63 three times), then sent its final offer.
- sellm sends exactly one new verified claim per message, so every round gets a fresh reason to concede.

## Gap 2 - our round-1 terms cost the supplier money, so its price goes up

In P01, P02, P05, P10 and P11 the supplier's first counter was higher than its opening (+3.15, +3.67, +2.50, +1.50, +2.00). Each time we asked for a term that costs the supplier:

| Case | What we asked for | What the winners do |
|---|---|---|
| P01 Brandlhuber (owner foundry) | payment 90 days | sellm on H29, same supplier: 14 days + effective date 2027-04-01. The supplier dropped -16.9 straight away; final score 99.7. Owner-run firms pay for fast payment. |
| P02 Nordmark (key account) | payment 30→90 days, no index clause | H04 twin: TMAR/Helllo accepted the supplier's copper index clause (20% share, 5% deadband) and scored ~0.78, while teams refusing it scored 0.46-0.69. HANDOFF.md already notes the index clause unlocked Nordmark in our run 1. |
| P10 capacity | lead time 54→42 **and** more volume (23400 vs 19890) | Coda: never push the constrained term, take the supplier's standard lead time (H15 0.89 vs sellm 0.55, where sellm pushed lead time like we did). We got a final_offer in round 1. |
| P05 RFQ | lead time 52→35 to the cheapest bidder | same capacity point |
| P11 quality | ppm 1500 + €500 chargeback | Fake on H19: looser ppm plus a chargeback bought the lowest price (0.55). sellm/Coda: 300 ppm, no chargeback. We ended at 47.49 vs the opening 47.00. |

Note: HANDOFF lists "payment-days friction" as tried and abandoned. The winners' rule is narrower: short payment only for owner-run, cash-hungry suppliers, which their letters signal ("Faster payment would help us more than anything"). It is not a general friction rule.

## Gap 3 - giving up valuable terms at the close

- **P18:** we moved payment from 90 to 30 days to close, then accepted. This is the same mistake as Helllo on H03, which scored 0 after "winning" a lower price.
- Winners hold 90 days with corporates and give it up only when the supplier puts a price on it explicitly. Codacabana on H24: "if we stick to 30 days... 17.90" → took 17.80.

## Gap 4 - anchor and pacing

- **Anchor:** we open at about 93% of the supplier's price; the winners open at 87-90% (sellm as low as 73-75% on price increases).
- **Fewer rounds:** we reach the final offer by round 2.4 on average, the winners by round 3.4-4.1. Each extra round with a new claim was worth about 2% to the winners.
- **Concession steps:** winners close about 20-30% of the gap per round, with shrinking steps and a new claim each time. Ours are erratic: +0.02, 0, +0.58 (P02), then +2.59 in one jump (P11).

## What we already do like the winners

- No zeros or timeouts. This was the top 3's biggest advantage over the field, and our timeout/walk guards (cfc132c and later) give us the same protection.
- We push the effective date to 2027-04-01 on price increases (P01). That is the right lever.
- We accept final offers rather than pushing past them (rule learned in practice run 1).
- Option packages and "what non-price terms would help?" questions (post-ask), like Fake's A/B/C packages.
- The Codacabana-style "binding volume, full demand" line.

## Priority order if these were ever implemented (not done - analysis only)

1. Fix index citations to include both `idx` IDs, so each one is a verified claim.
2. Stop citing the supplier's own offer as a rival quote, and stop citing quotes for other parts. Only cite another bidder's live offer in an RFQ.
3. Add notice_period (doc + ctr), volume_change (fc) and delivery_record (sc OTD only) claims to the brief.
4. One new verified claim per message, strongest first; never send a message without a new claim while evidence remains.
5. Payment days chosen by supplier type (owner-run: 10-14 days; corporate: 90 days and hold it).
6. Capacity cases: accept the supplier's standard lead time and volume.
7. Raw material and copper: accept a supplier-offered index clause with a deadband.
8. Open 3-5 points lower on price increases.
