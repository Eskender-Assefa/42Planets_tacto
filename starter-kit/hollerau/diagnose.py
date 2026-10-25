"""Where does our score go? Checks our maths against every scored practice deal.

    cd starter-kit && uv run python -m hollerau.diagnose

Free: reads results of our own sessions (GET, no practice session started, no Claude call).
1. Cost match - our arena_kit.cost total_cost on the deal terms vs the arena's c_deal; any gap is
   by component (so far only the supplier-health charge: the arena uses the true supplier).
2. Implied full cost - inverts relationship_cost on each revealed supplier-health charge: the full
   cost the arena uses, as a factor on our should_cost (feeds config full_cost_estimate.factor).
3. Lost score by component - deal cost breakdown vs the best package at the real floor price,
   in score units ((c_open - c_best) = 1.0).
"""

import json
import logging
import statistics
import sys
from pathlib import Path

from arena_kit.client import ArenaClient

from .calibrate import _threads_for
from .db import DBError, SupabaseDB
from .envelope import best_package, price_for_cost, safe_cost
from .kit import (
    JSONObject,
    closing_terms,
    complete_offer,
    cost_breakdown,
    load_env,
    relationship_cost,
    standard_terms,
    standing,
    total_cost,
)
from .package import Package, PackageError

log = logging.getLogger("hollerau.diagnose")
CASES = Path("data/cases/practice.json")


def implied_full_cost(case: JSONObject, terms: JSONObject, charge: float) -> float:
    """The supplier full cost at which the kit's relationship_cost equals the arena's charge."""
    buyer = case.get("buyer")
    rate = float(buyer.get("interest_rate") or 0.08) if isinstance(buyer, dict) else 0.08  # type: ignore[arg-type]
    std = {k: v for k, v in closing_terms(case, {}).items() if k != "unit_price"}
    price = terms.get("unit_price")
    lo, hi = 0.0, float(price) * 2 if isinstance(price, int | float) else 1e6
    for _ in range(60):
        mid = (lo + hi) / 2
        est = {"full_cost": mid, "interest_rate": rate, "standard": std}
        lo, hi = (mid, hi) if relationship_cost(case, terms, None, est) < charge else (lo, mid)  # type: ignore[arg-type]
    return hi


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    load_env()
    try:
        cases = {str(c["case_id"]): c for c in json.loads(CASES.read_text(encoding="utf-8"))}
        db = SupabaseDB()
        sessions = [r for r in db.select("cases", environment="eq.practice") if r.get("status") == "deal"]
        db.close()
        pkg = Package()
        client = ArenaClient()  # type: ignore[no-untyped-call]
    except (OSError, ValueError, DBError, PackageError) as e:
        print(f"FAIL {e}")
        return 1
    matched, factors, lost = 0, [], {}  # type: ignore[var-annotated]
    for row in sessions:
        cid, sid = str(row["case_id"]), str(row["session_id"])
        case = cases.get(cid)
        try:
            r = client.session(sid).get("result") or {}  # type: ignore[no-untyped-call]
        except Exception as e:  # one unreachable session must not stop the report
            log.warning("%s: %s", sid, e)
            continue
        if case is None or not r.get("terms"):
            continue
        terms, arena_bd = r["terms"], r.get("cost_breakdown") or {}
        ours = total_cost(case, terms)
        gap = float(r["c_deal"]) - ours
        if abs(gap) <= 1:
            matched += 1
        charge = float(arena_bd.get("relationship", 0.0))
        if charge > 1:
            sc = pkg.should_cost(str(case["parts"][0]), str(r["supplier_id"]))
            if sc and sc["unit_cost"]:
                factors.append(implied_full_cost(case, terms, charge) / sc["unit_cost"])
        threads = _threads_for(cid)
        if threads:
            opens = []
            for ev in threads.values():
                first = [m for m in ev if m.get("from") != "buyer" and m.get("term_sheets")][:1]
                if first:
                    std = standard_terms(first)
                    _, t = standing(first)
                    if isinstance(t.get("unit_price"), int | float):
                        opens.append((safe_cost(case, t, std), t, std))
            if opens:
                _, t, std = min(opens, key=lambda o: o[0])
                package, _ = best_package(case, complete_offer(case, t), float(t["unit_price"]), std, None)  # type: ignore[arg-type]
                floor = price_for_cost(case, package, float(r["c_best"]), std)
                if floor is not None:
                    ref = cost_breakdown(case, {**package, "unit_price": floor}, std)
                    span = float(r["c_open"]) - float(r["c_best"])
                    for k in set(ref) | set(arena_bd):
                        lost.setdefault(cid, {}).setdefault(k, []).append(
                            (float(arena_bd.get(k, 0)) - ref.get(k, 0)) / span
                        )
    print(f"1. cost match: {matched}/{len(sessions)} deals equal the arena's c_deal (+-1 EUR)")
    if factors:
        print(f"2. implied supplier full cost = should_cost x {statistics.mean(factors):.3f} (n={len(factors)})")
    print("3. lost score by component (mean per case; + costs us score)")
    for cid in sorted(lost):
        comps = {k: statistics.mean(v) for k, v in lost[cid].items() if abs(statistics.mean(v)) > 0.005}
        print(f"   {cid}: " + ", ".join(f"{k} {v:+.2f}" for k, v in sorted(comps.items(), key=lambda x: -abs(x[1]))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
