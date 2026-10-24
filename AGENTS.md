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

- Dashboard reads Cloud tables (suppliers, cases, audit_logs) from the browser with public read-only RLS and realtime invalidation; only the external Python runner writes, using a server-side key. Why: the pitch dashboard must be viewable without login while writes stay with the agent.
- Envelope score lives in src/lib/command.ts (envelopeScore) and is unit-tested. Why: one source of truth for the score shown on all views.
