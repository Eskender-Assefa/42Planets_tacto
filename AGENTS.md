<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

- Dashboard reads the external Hollerau backend (suppliers, cases, audit_logs, case_overview, wave_scores) via the read-only client in src/integrations/hollerau/; only the external Python runner writes. Why: the pitch dashboard must be viewable without login while writes stay with the agent.
- src/integrations/hollerau/types.ts is a byte-for-byte contract diffed against the backend repo; replace only from an explicitly supplied backend contract, byte-for-byte; never reformat it. Why: drift breaks the cross-repo sync check.
- Never recalculate cost-engine scores or cost estimates; negotiation insights may format stored scores as percentages, subtract stored deal and best costs, and aggregate best case scores and their mean. Why: presentation-only insights requested by the jury brief preserve backend ownership.
- src/integrations/supabase/* (Lovable Cloud) is not used for dashboard data anymore; leave the auto-generated files untouched. Why: they are platform-managed.

- Shared telemetry components format stored values, structured term sheets, and decision labels across wave and audit views. Why: one presentation path keeps old NULL rows and new telemetry consistent.
- Cost-bar coordinates are visual-only linear positioning of stored costs; no derived scores, savings, or cost estimates. Why: financial calculations remain backend-owned.
- Parse mechanisms and evidence in pure telemetry helpers; share supplier-separated Recharts/shadcn price paths between audit and pitch and batch case-summary audit reads by session IDs. Why: one presentation path avoids supplier mixing and N+1 reads.
- Build speech sentences in pure briefing helpers and reuse one browser-only speech hook across views; forward live events through the existing read-only subscription. Why: consistent narration, cancellation and queue ownership without external audio services.
