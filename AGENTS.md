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
- src/integrations/hollerau/types.ts is a byte-for-byte contract diffed against the backend repo; never edit or reformat it. Why: drift breaks the cross-repo sync check.
- No score, savings, or envelope maths in the frontend; the backend cost engine owns scores and the UI shows them as stored. Why: one source of truth for all cost calculations.
- src/integrations/supabase/* (Lovable Cloud) is not used for dashboard data anymore; leave the auto-generated files untouched. Why: they are platform-managed.
