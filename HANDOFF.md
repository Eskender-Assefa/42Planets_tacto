# Handoff - Hollerau Agentic Command (Tacto Negotiation Arena)

State on 2026-10-25 (Sunday). Code freeze **13:00** - submit the final commit hash.

## Current candidate
- `post-winners` (claims.py + owner payment + capacity lead time; see docs/winners_analysis) -
  offline tests + sim pass (sim 2.504, unchanged: the scripted sim ignores claims). NOT yet live-checked:
  keep it only if the same 5-case live check beats **2.290**; else revert to `post-ask`.
  Switches in config/strategy.json: `claims.enabled`, `owner_payment.enabled`, `capacity_respect.enabled`.
- `post-ask` (commit `1f62a23`): live check of P02+P07+P08+P10+P18
  summed to **2.290** (bar 2.19 from `post-guard`), no zero: P02 .19, P07 .62, P08 .54, P10 .66, P18 .27.
- Fallback: tag `post-guard` (best full run, 55.8 points).
- Leaderboard best-of: 62.8 (rank 12; 11th ~74.5).

## Remaining steps
1. 08:00: `uv run arena data` (Sunday release) -> check `Package.release_rows` reads it ->
   `uv run pytest -q` (81 pass expected), `uv run ruff check`, `uv run --with mypy mypy --strict hollerau`.
2. Ask the user before ANY live practice run (each costs practice sessions + Claude credits).
   Optional: one practice rehearsal of the final setup.
3. Freeze: tag the final commit (e.g. `final`), push with tags, give the user `git rev-parse HEAD`.
4. Final (organisers' instructions): `uv run python -m hollerau.run --set final --parallel 10`.
5. Optional idea: P02 is weak - in run 1 the index clause unlocked Nordmark's price; the current
   strategic target omits it.

## Working setup
- Work in `starter-kit/`. Bash: `export PATH="$LOCALAPPDATA/Microsoft/WinGet/Packages/astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe:$PATH"`.
- Free: `uv run pytest -q`, `uv run python -m hollerau.diagnose`, `uv run python -m hollerau.calibrate`,
  local sim `uv run arena-sim serve --data data/package` + `uv run python -m hollerau.run --set sim -v`.
- Live: `uv run python -m hollerau.run --set practice --cases case:P02,... --parallel N -v > data/X.log`.
- Never edit `arena_kit`; never print/commit keys (`starter-kit/.env`); never amend pushed commits;
  tag every new state. Use Edit/patch files rather than heredoc Python patches (`\n` escapes break).

## Tried and abandoned (don't redo without new evidence)
Bluffing competitors, v3 lever give-aways, equal-cost variants, payment-days friction,
leverage-position aggressiveness, adversarial prompt injection (declined).
