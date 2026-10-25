"""Fit the supplier-floor estimate to every practice case the arena has scored.

    cd starter-kit && uv run python -m hollerau.calibrate        # prints + writes config/calibration.json

No arena session, no Claude call: reads the recorded threads (data/cases/<case>_threads.json, fetched
from our own practice sessions) and the c_best the arena revealed in each result (Supabase `cases`).
For each case: the cheapest opening sheet -> our best lever package at that price -> the price at
which that package costs c_best (bisection on arena_kit.cost) -> ratio vs. the opening price.
Per category_goal the mean ratio becomes the floor estimate used live (envelope.floor_estimate):
C_best is never known before a case ends, so this is the honest stand-in (leverage_fix.txt).
"""

import json
import logging
import statistics
import sys
from pathlib import Path
from typing import TypedDict

from .db import DBError, SupabaseDB
from .envelope import best_package, price_for_cost, safe_cost
from .kit import JSONObject, Message, complete_offer, load_env, standard_terms, standing

log = logging.getLogger("hollerau.calibrate")

CASES = Path("data/cases/practice.json")
THREADS = Path("data/cases")
OUT = Path(__file__).parent / "config" / "calibration.json"


class CasePoint(TypedDict):
    case_id: str
    goal: str
    opening_price: float
    floor_price: float
    ratio: float  # floor price / opening price - 1


class GoalFit(TypedDict):
    floor_ratio: float
    n: int
    min: float
    max: float
    cases: list[str]


def _threads_for(case_id: str) -> dict[str, list[Message]] | None:
    short = case_id.removeprefix("case:")
    for name in (f"{short}_threads.json", f"{short}run1_threads.json"):
        path = THREADS / name
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
    return None


def point(case: JSONObject, threads: dict[str, list[Message]], c_best: float) -> CasePoint | None:
    """The real floor of one case, as a price ratio to the cheapest opening."""
    opens: list[tuple[float, JSONObject, JSONObject]] = []
    for events in threads.values():
        first = [m for m in events if m.get("from") != "buyer" and m.get("term_sheets")][:1]
        if not first:
            continue
        std = standard_terms(first)
        _, terms = standing(first)
        if isinstance(terms.get("unit_price"), int | float):
            opens.append((safe_cost(case, terms, std), terms, std))
    if not opens:
        return None
    _, terms, std = min(opens, key=lambda o: o[0])
    opening = float(terms["unit_price"])  # type: ignore[arg-type]
    package, _ = best_package(case, complete_offer(case, terms), opening, std, None)
    floor = price_for_cost(case, package, c_best, std)
    if floor is None:
        return None
    buyer = case.get("buyer")
    goal = str(buyer.get("category_goal")) if isinstance(buyer, dict) else "unknown"
    return {
        "case_id": str(case.get("case_id")),
        "goal": goal,
        "opening_price": opening,
        "floor_price": floor,
        "ratio": round(floor / opening - 1, 4),
    }


def fit(points: list[CasePoint]) -> dict[str, GoalFit]:
    by: dict[str, list[CasePoint]] = {}
    for p in points:
        by.setdefault(p["goal"], []).append(p)
    return {
        goal: {
            "floor_ratio": round(statistics.mean(p["ratio"] for p in ps), 4),
            "n": len(ps),
            "min": min(p["ratio"] for p in ps),
            "max": max(p["ratio"] for p in ps),
            "cases": [p["case_id"] for p in ps],
        }
        for goal, ps in sorted(by.items())
    }


def revealed_c_best(db: SupabaseDB) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in db.select("cases", environment="eq.practice"):
        cid, cb = row.get("case_id"), row.get("c_best")
        if isinstance(cid, str) and isinstance(cb, int | float):
            out[cid] = float(cb)
    return out


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    load_env()
    try:
        cases = {str(c["case_id"]): c for c in json.loads(CASES.read_text(encoding="utf-8"))}
        db = SupabaseDB()
        c_best = revealed_c_best(db)
        db.close()
    except (OSError, ValueError, DBError) as e:
        print(f"FAIL {e}")
        return 1
    points = []
    for cid, cb in sorted(c_best.items()):
        threads = _threads_for(cid)
        if threads is None or cid not in cases:
            print(f"  skip {cid}: no recorded thread")
            continue
        p = point(cases[cid], threads, cb)
        if p is not None:
            points.append(p)
            o, fl = p["opening_price"], p["floor_price"]
            print(f"  {cid} {p['goal']:<14} opening {o:>9.2f} floor {fl:>9.2f} {p['ratio']:+.1%}")
    fits = fit(points)
    for goal, f in fits.items():
        print(f"{goal:<14} n={f['n']} floor ratio {f['floor_ratio']:+.1%} (range {f['min']:+.1%} .. {f['max']:+.1%})")
    OUT.write_text(json.dumps(fits, indent=2), encoding="utf-8")
    print(f"written {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
