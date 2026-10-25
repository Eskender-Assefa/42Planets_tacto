# Lovable prompt 005 - voice briefing without ElevenLabs

Paste everything below the line into Lovable. No schema change and no API key: the voice runs in the
browser. Afterwards pull the subtree with `bash scripts/sync-dashboard.sh`.

---

We no longer use ElevenLabs. Make the voice briefing a first-class feature of the dashboard itself,
using the browser's built-in speech (Web Speech API, `window.speechSynthesis`). It must work with no
API key, no network call for audio, and on a projector laptop during our pitch.

Ground rules, same as before:
- Read-only on our Hollerau Supabase data; no mock data; NULL renders as "-" on screen and is simply
  skipped in speech.
- Do NOT change `src/integrations/hollerau/types.ts` and add no tables, columns, edge functions or
  external services. Do not use the Lovable Cloud Supabase client.
- Remove every ElevenLabs mention: the placeholder sentence on `/briefing/$sessionId`, the
  "Temporary browser voice" comment, and the roadmap item (mark it done as "Browser voice briefing").
- Keep all existing routes and tests green; new pure helpers get unit tests in `src/test/`.

## 1. A spoken script built from the data (pure helper)

Add `buildBriefingScript(c: CaseOverview, logs: AuditLog[], supplierName: (id: string) => string,
mode: "summary" | "full"): string[]` in `src/lib/briefing.ts`. It returns sentences (one array item
each) written for the ear: short sentences, no symbols, no IDs, no " | " fragments, no raw
`mathematical_justification`. Use `parseMechanisms` and `extractEvidence` from `src/lib/telemetry.ts`.

Money is spoken in words-friendly form: `€1,522,963` → "1.52 million euros", `€249,273` → "249
thousand euros", unit prices `5.45` → "5 euros 45". Percentages: "68 percent".

`summary` mode (default), in this order, skipping any sentence whose data is missing:
1. "Briefing for <title>, with <supplier names>." and the case type in plain words (price increase,
   renewal, request for quotation, bundling, raw material, capacity, quality).
2. Outcome: deal → "We closed a deal with <supplier> after <n> rounds." walked_away → "We walked away
   because the alternative was cheaper." no_deal → "The case ended without a deal." active → "The
   negotiation is still running, round <n>."
3. Score: "We captured <score×100> percent of the possible saving, <c_deal − c_best> above the best
   possible cost." (deals only).
4. Evidence: "We argued with <k> data points, <verified> of them verified by the supplier." from the
   newest row's `claims`; then the kinds used, in order of first use, as plain labels (index fall,
   notice period, cost estimate, volume forecast, delivery record, defect rate, order history, a
   rival's live offer, supplier news) - e.g. "Our arguments: an index fall, a volume forecast and the
   supplier's delivery record."
5. Movement: if any row has paced moves → "We moved every round and never took a concession back."
   If any row has `decision_source` = "rule" with `observed_barrier` "Supplier declared its final
   offer." → "When the supplier declared its final offer, we took it rather than risk a walk-away."
6. Final terms, one sentence from the last `proposed_terms` (or the accepted `supplier_terms`): unit
   price, payment days, contract months, and any index clause ("with a steel index clause, 5 percent
   deadband") - only the fields present.

`full` mode: sentences 1-2, then one sentence per turn in order: "Round <n>. <supplier> offered <their
unit price>. We countered at <our unit price>, citing <claim label>." (+ " We raised our own price
from X to Y to keep the negotiation moving." when paced; + "We accepted." / "We walked away." on those
actions), then sentences 3-6.

Tests (with small fixtures built from real-looking rows): money formatting; a deal case produces the
outcome, score and evidence sentences; a row with `"paced to min C EUR 324,997.80: 5.30->5.45"`
produces the "never took a concession back" sentence; no output sentence contains "|", "idx:", "sc:"
or "EUR".

## 2. Briefing room (`/briefing/$sessionId`) with real playback controls

Replace the current Play button logic with a small speech player hook `useSpeech(sentences)`:
- Play / Pause / Resume / Stop; Previous and Next sentence; speed 0.8x / 1x / 1.2x.
- Voice picker: list `speechSynthesis.getVoices()` (they load async - listen to `voiceschanged`),
  default to the first English voice whose name contains "Natural", "Neural", "Google" or "Online",
  else any `en-GB`/`en-US` voice; remember the choice in `localStorage`.
- Speak sentence by sentence (one `SpeechSynthesisUtterance` per sentence) and highlight the current
  sentence in the transcript below the button; clicking a sentence starts from there.
- Mode toggle "Summary / Full negotiation" (section 1).
- If `speechSynthesis` is missing, show the transcript with a short note "This browser has no
  built-in voice" and hide the controls - never throw.
- Cancel speech on unmount and when the session changes (Chrome keeps speaking otherwise).
- Keep the large round play button as the main control; the rest sits in a compact toolbar.

## 3. Voice everywhere it helps

- Pitch view (`/pitch/$sessionId`): a "▶ Narrate" button in the header that plays the `full` script
  with the same hook and highlights the matching turn in the story list while it speaks.
- Audit page: a small "🔊" button per turn card that speaks just that turn's sentence.
- Wave / live view: a "Live narration" toggle (off by default). When on, each new `audit_logs` row
  that arrives through the existing realtime subscription is spoken as one short sentence: "<case
  title>: <supplier> offered <price>, we countered <price>." and for a finished case "<case title>:
  deal at <price>, <score> percent." Queue sentences, never overlap, drop anything older than 60
  seconds so narration does not lag behind a fast wave.

## Done when
- No "ElevenLabs" string remains in `src/` or `roadmap.md`.
- All tests pass (old and new), `bun run build` succeeds.
- On a real P07 session the summary script reads naturally, mentions the claims and the moving
  pacing, and plays, pauses and resumes in Chrome and Edge.
