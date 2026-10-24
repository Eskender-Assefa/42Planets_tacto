# Lovable prompt 003 - concession velocity is already a percentage

Paste everything below the line into Lovable.

---

Fix one unit bug: `audit_logs.concession_velocity` and `case_overview.last_concession_velocity` are
stored **already in percent of C_open per round** (1.97 means 1.97 %, 0.004 means 0.004 %). In
`src/lib/telemetry.ts`, `velocityLabel` must not multiply by 100: `velocityLabel(1.97)` should return
`"1.97% of C_open / round"` and `velocityLabel(0.004)` should return `"0.00% of C_open / round"`.
Update `src/test/telemetry.test.ts` accordingly. No other changes; `src/integrations/hollerau/types.ts`
stays exactly as it is.
