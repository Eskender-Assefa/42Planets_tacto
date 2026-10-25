"""Step 2 of the turn - supplier telemetry, computed in Python from the thread.

- concession velocity: how much C the supplier's sheet dropped since its previous one, as % of
  c_open (so cases of any size compare); averaged velocity over the thread too
- mindset: opening / yielding / stalled / critical_breakoff (final_offer or warning signals)
- claims: the arena's verdicts on the data we cited (verified / irrelevant / contradicted /
  duplicate); only the first 3 IDs of a message are checked
"""

import math
from typing import Literal, TypedDict

from .envelope import safe_cost, supplier_sheets
from .kit import JSONObject, Message, latest, moves_left, standard_terms
from .profiles import config

Mindset = Literal["opening", "yielding", "stalled", "critical_breakoff", "unread"]  # unread: quarantined
CRITICAL_STATUSES = frozenset({"final_offer", "walked_away", "no_bid"})


class ClaimTally(TypedDict):
    verified: int
    irrelevant: int
    contradicted: int
    duplicate: int  # cited before in this case: earns nothing


class Telemetry(TypedDict):
    supplier_id: str
    status: str | None
    rounds: int  # supplier sheets so far
    moves_left: int
    sheet_costs: list[float]  # C of each supplier sheet, oldest first
    concession_velocity: float | None  # last step, % of c_open
    mean_velocity: float | None  # whole thread, % of c_open per step
    mindset: Mindset
    claims: ClaimTally


def _claims(events: list[Message]) -> ClaimTally:
    tally: ClaimTally = {"verified": 0, "irrelevant": 0, "contradicted": 0, "duplicate": 0}
    for m in events:
        results = m.get("claim_results")
        if not isinstance(results, list):
            continue
        for r in results:
            verdict = r.get("result") if isinstance(r, dict) else None
            if verdict in tally:
                tally[verdict] += 1  # type: ignore[literal-required]
    return tally


def telemetry(case: JSONObject, supplier_id: str, events: list[Message], c_open: float | None) -> Telemetry:
    std = standard_terms(events)
    costs = [c for c in (safe_cost(case, t, std) for _, t in supplier_sheets(events)) if math.isfinite(c)]
    status = latest(events).get("status") if events else None
    status_s = status if isinstance(status, str) else None
    base = c_open or (costs[0] if costs else None)

    velocity = mean = None
    if base and len(costs) >= 2:
        velocity = round((costs[-2] - costs[-1]) / base * 100, 4)
        mean = round((costs[0] - costs[-1]) / base * 100 / (len(costs) - 1), 4)

    cfg = config()["telemetry"]
    mindset: Mindset
    if not config()["mindset_inference"]["enabled"]:
        mindset = "unread"
    elif status_s in CRITICAL_STATUSES:
        mindset = "critical_breakoff"
    elif velocity is None:
        mindset = "opening"
    elif velocity < cfg["stalled_velocity_pct"]:
        mindset = "stalled"
    else:
        mindset = "yielding"

    return {
        "supplier_id": supplier_id,
        "status": status_s,
        "rounds": len(costs),
        "moves_left": moves_left(case, events) if events else 0,
        "sheet_costs": [round(c, 2) for c in costs],
        "concession_velocity": velocity,
        "mean_velocity": mean,
        "mindset": mindset,
        "claims": _claims(events),
    }
