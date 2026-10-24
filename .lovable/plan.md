# Hollerau Agentic Command — Dashboard Plan

Note: I can't write to your desktop folder "42Planets_tacto". Everything is built in this Lovable project; connect GitHub (Settings → GitHub) and pull it into that folder.

## What we build
A dark, industrial "command center" dashboard with four views, driven by the session data shape you provided (session, supplier, metrics, audit_trail).

1. **ERP Master Grid** (`/`) — table of all cases: supplier, segment, country, wave, open cost, current offer, floor, score, status.
2. **Live Wave Terminal** (`/wave`) — 10-card grid. Each card: supplier name/segment/country, turn number, countdown bar from `seconds_left`, cost envelope bar (open → current offer → best floor), score gauge, mindset badge (Stalled / Yielding / Critical_Breakoff), status (Active / Closed / Failed).
3. **Traceability Audit** (`/audit/$sessionId`) — per-turn timeline: price offered, local cost, concession velocity, mindset, observed barrier, strategic intent, mathematical justification, email sent.
4. **Voice Briefing Room** (`/briefing/$sessionId`) — "Play briefing" button that reads a natural summary of the audit trail aloud (ElevenLabs, added in a later step).

## Layout states (from your data block)
- Active: live pulsing border, ticking countdown.
- Stalled mindset: amber accent, barrier text highlighted.
- Under 60 s left: countdown turns red.
- Closed/Failed: card dims, shows final score.
- Score shown as % of the way from open cost to best floor.

## Data
- Lovable Cloud database with tables `suppliers`, `cases` (adds turn_number, seconds_left, current_offer, current_score, status), `audit_logs`, matching your document's schema.
- Live updates pushed to the dashboard as your Python runner inserts rows.
- Seeded with 10 demo cases (including Gießerei Brandlhuber, case_wave1_04) so the screens look real before Sunday.
- Your Python runner writes using a secret key you keep on your laptop; I'll provide a short Python snippet.

## Design
Dark graphite background, signal-orange accent, monospaced numbers, tight grid — factory control-room feel, not a generic SaaS look.

## Technical details
- TanStack routes per view, realtime subscription on `cases` and `audit_logs`.
- Public read access for the dashboard (demo/pitch), writes only via service key from the runner.
- ElevenLabs voice via a server function once you provide an API key.
