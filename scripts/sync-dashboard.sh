#!/usr/bin/env bash
# Pull the latest Lovable dashboard into dashboard/ and verify it still matches the backend.
#
#   bash scripts/sync-dashboard.sh          # pull + verify
#   bash scripts/sync-dashboard.sh --push   # also send local dashboard/ commits back to Lovable
#
# Exit code 0 = in sync and green. Run it before you start working and before every commit.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

CONTRACT_BACKEND="db/types.ts"
CONTRACT_DASHBOARD="dashboard/src/integrations/hollerau/types.ts"

if [ -n "$(git status --porcelain)" ]; then
  echo "Working tree not clean - commit or stash first (subtree pull needs a clean tree)." >&2
  exit 1
fi

echo "== 1/4 pull Lovable -> dashboard/"
git subtree pull --prefix=dashboard dashboard main -m "chore: sync dashboard from Lovable" --quiet

if [ "${1:-}" = "--push" ]; then
  echo "== push dashboard/ -> Lovable"
  git subtree push --prefix=dashboard dashboard main
fi

echo "== 2/4 types contract ($CONTRACT_BACKEND vs $CONTRACT_DASHBOARD)"
if [ ! -f "$CONTRACT_DASHBOARD" ]; then
  echo "MISSING: Lovable has not created $CONTRACT_DASHBOARD yet (see docs/lovable/001-*.md)." >&2
  contract_ok=0
elif ! diff -u --strip-trailing-cr "$CONTRACT_BACKEND" "$CONTRACT_DASHBOARD"; then
  echo "DRIFT: the dashboard's types differ from db/types.ts. Paste the new db/types.ts into Lovable." >&2
  contract_ok=0
else
  echo "in sync"
  contract_ok=1
fi

echo "== 3/4 install + test + typecheck"
(cd dashboard && bun install --frozen-lockfile >/dev/null && bun run test && bun x tsc --noEmit)

echo "== 4/4 build"
(cd dashboard && bun run build >/dev/null && echo "build ok")

# The build regenerates this route file; keep the committed (Lovable) version.
git checkout -- dashboard/src/routeTree.gen.ts 2>/dev/null || true

[ "$contract_ok" = 1 ] || exit 2
echo "Dashboard in sync and green."
