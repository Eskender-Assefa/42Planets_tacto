"""v3 trade-off matrix: give the supplier a lever it wants only for a matching price cut.

Desktop\\Tacto\\v3_improvements.txt: payment days as a discount lever, the index clause as a
bargaining chip, horizon length (commitment beyond the horizon costs us nothing - a free chip),
incoterm as a freight swap. All euros come from arena_kit.cost via hollerau.envelope.safe_cost:

  give_cost   C(our target sheet with the lever changed) - C(our target sheet)        [EUR]
  slope       C at price + 1 EUR - C at price  (units the price applies to, incl. dates)
  break-even  give_cost / slope                                                       [EUR/unit]
  ask         max(break-even x premium, the lever's default ask), capped at max_cut_pct

A swap is offered only if its sheet costs us less than the supplier's standing sheet.
"""

import math
from typing import TypedDict

from .envelope import ThreadEnvelope, lever_fields, safe_cost
from .kit import JSONObject, JSONValue, Message, complete_offer
from .profiles import SwapsConfig

FREE_EUR = 1.0  # a lever change costing us less than this is a free chip


class Swap(TypedDict):
    field: str
    value: JSONValue
    wanted: bool  # the supplier asked for this lever (text signal or its own sheet/terms)
    give_cost_eur: float  # what giving it costs us at our target price
    breakeven_per_unit: float  # price cut that just pays for it
    ask_price: float
    cut_pct: float  # ask vs. the supplier's standing price
    sheet: JSONObject
    c_true: float


def wants(events: list[Message], cfg: SwapsConfig, last_n: int = 2) -> set[str]:
    """Levers the supplier's latest messages ask for, by wording (config patterns)."""
    texts = [str(m.get("body") or "").lower() for m in events if m.get("from") != "buyer"][-last_n:]
    blob = " ".join(texts)
    return {f for f, pats in cfg["want_patterns"].items() if any(p in blob for p in pats)}


def _options(case: JSONObject, field: str) -> list[JSONValue]:
    opts = case.get("term_options")
    values = opts.get(field) if isinstance(opts, dict) else None
    return values if isinstance(values, list) else []


def _price_slope(case: JSONObject, sheet: JSONObject, te: ThreadEnvelope) -> float | None:
    price = sheet.get("unit_price")
    if not isinstance(price, int | float):
        return None
    lo = safe_cost(case, sheet, te["standard"], te["supplier_estimate"])
    hi = safe_cost(case, {**sheet, "unit_price": price + 1.0}, te["standard"], te["supplier_estimate"])
    slope = hi - lo
    return slope if math.isfinite(slope) and slope > 0 else None


def swaps(case: JSONObject, te: ThreadEnvelope, events: list[Message], cfg: SwapsConfig) -> list[Swap]:
    """The best (up to 3) priced trades for this thread, wanted levers first."""
    base, standing = te["target_terms"], te["standing_terms"]
    tp, sp, c_stand = te["target_price"], te["standing_price"], te["c_true_standing"]
    if not cfg["enabled"] or not base or tp is None or sp is None or c_stand is None:
        return []
    c_base = safe_cost(case, base, te["standard"], te["supplier_estimate"])
    slope = _price_slope(case, base, te)
    if not math.isfinite(c_base) or slope is None:
        return []
    asked = wants(events, cfg)
    out: list[Swap] = []
    for field in lever_fields(case):
        for value in _options(case, field):
            if value == base.get(field):
                continue
            theirs = value == standing.get(field) or value == te["standard"].get(field)
            sheet = complete_offer(case, {**base, field: value})
            give = safe_cost(case, sheet, te["standard"], te["supplier_estimate"]) - c_base
            if not math.isfinite(give) or give < -FREE_EUR:
                continue  # cheaper for us: best_package would already take it - not a give
            wanted = field in asked or theirs
            if not wanted and give > FREE_EUR:
                continue  # a costly lever nobody asked for is no bargaining chip
            breakeven = max(give, 0.0) / slope
            default = max(cfg["default_ask_pct"].get(field, 0.0) / 100 * sp, cfg["default_ask_eur"].get(field, 0.0))
            cut = min(max(breakeven * cfg["premium"], default), sp * cfg["max_cut_pct"] / 100)
            ask = round(max(tp, sp - cut), 2)
            priced = complete_offer(case, {**sheet, "unit_price": ask})
            c_true = safe_cost(case, priced, te["standard"], te["supplier_estimate"])
            if not math.isfinite(c_true) or c_true >= c_stand:
                continue
            out.append(
                {
                    "field": field,
                    "value": value,
                    "wanted": wanted,
                    "give_cost_eur": round(give, 2),
                    "breakeven_per_unit": round(breakeven, 4),
                    "ask_price": ask,
                    "cut_pct": round((sp - ask) / sp * 100, 2),
                    "sheet": priced,
                    "c_true": round(c_true, 2),
                }
            )
    out.sort(key=lambda s: (not s["wanted"], s["c_true"]))
    return out[:3]


def stalled(velocity: float | None, sent: int, cfg: SwapsConfig) -> bool:
    """A concession step below the trigger after we have written at least once."""
    return sent >= 1 and velocity is not None and velocity < cfg["trigger_velocity_pct"]
