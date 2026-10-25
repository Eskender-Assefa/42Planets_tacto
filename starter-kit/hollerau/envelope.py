"""Step 6 - the financial envelope of a turn. Every euro comes from arena_kit.cost via hollerau.kit;
this module only chooses which term sheets to price.

Per supplier thread:
- c_standing: C of the supplier's standing sheet (what the arena scores, without relationship term)
- c_true_standing / penalty_at_offer: C including our estimate of the supplier-health charge
  (stabilise / secure_supply cases only - arena_kit.cost.relationship_cost)
- c_opening: C of its first sheet; c_open = the cheapest opening over all threads (the score's 0)
- price_floor_est / c_floor_est: our estimate of how low the supplier can go (should_cost based) -
  the live stand-in for the hidden c_best
- target: the sheet we should be asking for this round, its price and C
- levers: what each allowed value of each non-price field is worth to us, in EUR
"""

import itertools
import logging
import math
from typing import Literal, TypedDict

from .kit import (
    JSONObject,
    JSONValue,
    Message,
    SupplierEstimate,
    Threads,
    closing_terms,
    complete_offer,
    cost_breakdown,
    must_haves_ok,
    standard_terms,
    standing,
    total_cost,
)
from .package import Package, PackageError
from .profiles import Protocol, config

log = logging.getLogger("hollerau.envelope")

MAX_COMBOS = 400  # lever packages priced per candidate price
FULL_WAVE_S, CLOSE_S = 480.0, 90.0  # the final's wave cap and the kit's close-before-cap margin


Position = Literal["strong", "balanced", "vulnerable"]


class LeverOption(TypedDict):
    field: str
    value: JSONValue
    delta_eur: float  # C change vs. the supplier's standing sheet, same price (negative = saves us)


class OfferOption(TypedDict):
    sheet_id: str | None
    terms: JSONObject
    c: float | None  # C as the arena scores it
    c_true: float | None  # incl. our supplier-health estimate
    coverage_pct: float | None  # share of our need over the horizon this sheet covers
    uncovered_eur: float | None  # what the uncovered rest costs at the fallback price (+ risk)


class ThreadEnvelope(TypedDict):
    supplier_id: str
    sheet_id: str | None
    standing_terms: JSONObject
    standard: JSONObject
    standing_price: float | None
    c_standing: float | None
    c_true_standing: float | None
    penalty_at_offer: float | None
    c_opening: float | None
    supplier_estimate: SupplierEstimate | None
    full_cost_ref: str | None  # citable 'cost:<part>' behind the estimate
    price_floor_est: float | None
    c_floor_est: float | None
    target_price: float | None
    target_terms: JSONObject | None
    c_target: float | None
    levers: list[LeverOption]
    offers: list[OfferOption]  # every sheet of the supplier's latest message, priced
    coverage_pct: float | None  # the standing sheet's coverage of our need over the horizon
    uncovered_eur: float | None
    target_coverage_pct: float | None


class Envelope(TypedDict):
    c_open: float | None
    c_alt: float | None
    progress: float  # 0 = first round, 1 = landing (last rounds or the wave cap is near)
    best_supplier: str | None  # cheapest standing sheet by true C
    leverage_gap_pct: float | None  # (C_alt - C_open) / C_open; None without an alternative
    position: Position  # strong / balanced / vulnerable (strong_factors_plus.txt)
    threads: dict[str, ThreadEnvelope]


def _num(v: JSONValue) -> float | None:
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) else None


def _finite(c: float) -> float | None:
    return round(c, 2) if math.isfinite(c) else None


def safe_cost(
    case: JSONObject, terms: JSONObject, std: JSONObject | None = None, est: SupplierEstimate | None = None
) -> float:
    """total_cost, or inf for a sheet the cost model cannot price (missing price, bad option)."""
    try:
        return total_cost(case, terms, std, est)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as e:
        log.debug("unpriceable sheet %s: %s", terms, e)
        return math.inf


def supplier_sheets(events: list[Message]) -> list[tuple[str | None, JSONObject]]:
    """(term_sheet_id, terms) of the first sheet of every supplier message, oldest first."""
    out: list[tuple[str | None, JSONObject]] = []
    for m in events:
        sheets = m.get("term_sheets")
        if m.get("from") == "buyer" or not isinstance(sheets, list) or not sheets:
            continue
        first = sheets[0]
        if isinstance(first, dict) and isinstance(first.get("terms"), dict):
            sid = first.get("term_sheet_id")
            out.append((sid if isinstance(sid, str) else None, first["terms"]))  # type: ignore[arg-type]
    return out


def latest_sheets(events: list[Message]) -> list[tuple[str | None, JSONObject]]:
    """Every sheet (main + alternatives) of the supplier's latest message - the kit's standing()
    reads only the first."""
    last = next((m for m in reversed(events) if m.get("from") != "buyer"), None)
    sheets = last.get("term_sheets") if last else None
    out: list[tuple[str | None, JSONObject]] = []
    for s in sheets if isinstance(sheets, list) else []:
        if isinstance(s, dict) and isinstance(s.get("terms"), dict):
            sid = s.get("term_sheet_id")
            out.append((sid if isinstance(sid, str) else None, s["terms"]))  # type: ignore[arg-type]
    return out


def c_alt(case: JSONObject) -> float | None:
    buyer = case.get("buyer")
    alt = buyer.get("alternative") if isinstance(buyer, dict) else None
    terms = alt.get("terms") if isinstance(alt, dict) else None
    if not isinstance(terms, dict) or _num(terms.get("unit_price")) is None:
        return None
    return _finite(safe_cost(case, terms))


def c_open(case: JSONObject, threads: Threads) -> float | None:
    """The cheapest opening sheet over all threads, priced with each supplier's standard terms."""
    costs = []
    for events in threads.values():
        sheets = [t for _, t in supplier_sheets(events) if _num(t.get("unit_price")) is not None]
        if sheets:
            costs.append(safe_cost(case, sheets[0], standard_terms(events)))
    finite = [c for c in costs if math.isfinite(c)]
    return round(min(finite), 2) if finite else None


def coverage(case: JSONObject, terms: JSONObject, std: JSONObject | None) -> tuple[float | None, float | None]:
    """(share of our need over the horizon the sheet covers, EUR the uncovered rest costs).
    Uncovered need is bought at the fallback price plus the category's fallback risk -
    arena_kit.cost prices it; this only reads the parts out (strong_factors_plus.txt, factor 1)."""
    buyer = case.get("buyer")
    if not isinstance(buyer, dict):
        return None, None
    need, horizon = _num(buyer.get("need_per_year")), _num(buyer.get("horizon_years"))
    t = closing_terms(case, terms, std)
    vol, months = _num(t.get("volume_per_year")), _num(t.get("contract_months"))
    if not need or not horizon or vol is None or months is None:
        return None, None
    years = min(months / 12 if months else 1.0, horizon)  # a single order counts as one year's lot
    pct = round(min(vol, need) * years / (need * horizon), 4)
    if _num(t.get("unit_price")) is None:
        return pct, None
    try:
        parts = cost_breakdown(case, terms, std)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return pct, None
    return pct, round(parts.get("uncovered_need", 0.0) + parts.get("fallback_risk", 0.0), 2)


def leverage_position(c_open_v: float | None, c_alt_v: float | None) -> tuple[float | None, Position]:
    """Our alternative vs. the cheapest opening (strong_factors_plus.txt, factor 2)."""
    if c_open_v is None or c_alt_v is None or c_open_v <= 0:
        return None, "vulnerable"  # no alternative: a breakoff leaves us exposed
    gap = round((c_alt_v - c_open_v) / c_open_v * 100, 2)
    if gap < 0:
        return gap, "strong"
    if gap > config()["leverage"]["vulnerable_above_pct"]:
        return gap, "vulnerable"
    return gap, "balanced"


def is_relationship_case(case: JSONObject, proto: Protocol) -> bool:
    buyer = case.get("buyer")
    return bool(
        proto["segment"].get("relationship")
        and isinstance(buyer, dict)
        and buyer.get("relationship_eur_per_point")
        and buyer.get("sustainable_margin_pct")
    )


def estimate_supplier(
    case: JSONObject, pkg: Package | None, supplier_id: str, country: str | None, std: JSONObject
) -> tuple[SupplierEstimate | None, str | None]:
    """Our estimate of the supplier's full cost and money cost, from should_cost."""
    parts = case.get("parts")
    if pkg is None or not isinstance(parts, list) or len(parts) != 1:
        return None, None  # bundles: no single should-cost
    try:
        sc = pkg.should_cost(str(parts[0]), supplier_id)
    except PackageError as e:
        log.warning("should_cost lookup failed: %s", e)
        return None, None
    if sc is None or sc["unit_cost"] is None:
        return None, None
    cfg = config()
    full = float(sc["unit_cost"])
    if sc["supplier_id"] is None:  # generic estimate: German cost base -> supplier's country
        factors = cfg["country_cost_factor"]
        full *= factors.get(country or "", 1.0) / factors.get(sc["cost_base"] or "DE", 1.0)
    if cfg["full_cost_estimate"]["use_lower_bound"] and sc["confidence_pct"]:
        full *= 1 - sc["confidence_pct"] / 100
    buyer = case.get("buyer")
    rate = _num(buyer.get("interest_rate")) if isinstance(buyer, dict) else None
    standard = {k: v for k, v in closing_terms(case, {}, std).items() if k != "unit_price"}
    return {"full_cost": round(full, 4), "interest_rate": rate or 0.08, "standard": standard}, sc["id"]


def lever_fields(case: JSONObject) -> list[str]:
    neg, opts = case.get("negotiable"), case.get("term_options")
    if not isinstance(neg, list) or not isinstance(opts, dict):
        return []
    return [str(f) for f in neg if f != "unit_price" and isinstance(opts.get(str(f)), list) and opts[str(f)]]


def _options(case: JSONObject, field: str) -> list[JSONValue]:
    opts = case.get("term_options")
    values = opts.get(field) if isinstance(opts, dict) else None
    return values if isinstance(values, list) else []


def lever_table(case: JSONObject, base: JSONObject, std: JSONObject, est: SupplierEstimate | None) -> list[LeverOption]:
    """What each allowed value of each non-price field changes in C, at the base sheet's price."""
    c_base = safe_cost(case, base, std, est)
    out: list[LeverOption] = []
    if not math.isfinite(c_base):
        return out
    for field in lever_fields(case):
        for value in _options(case, field):
            c = safe_cost(case, {**base, field: value}, std, est)
            if math.isfinite(c):
                out.append({"field": field, "value": value, "delta_eur": round(c - c_base, 2)})
    return out


def _distance(terms: JSONObject, base: JSONObject, fields: list[str]) -> float:
    """How far a package moves the non-price fields from the supplier's sheet (0 = unchanged)."""
    d = 0.0
    for f in fields:
        a, b = terms.get(f), base.get(f)
        if isinstance(a, int | float) and isinstance(b, int | float) and not isinstance(a, bool):
            d += abs(a - b) / max(abs(b), 1.0)
        elif a != b:
            d += 1.0
    return d


def best_package(
    case: JSONObject, base: JSONObject, price: float, std: JSONObject, est: SupplierEstimate | None
) -> tuple[JSONObject, float]:
    """The lever combination with the lowest C at `price` (a complete, snapped term sheet) that
    keeps the must-haves. Ties (within 1 EUR) go to the package closest to the supplier's sheet:
    what is free for us is given away (P11, run 2: a chargeback above our defect cost made ppm
    worthless to us, yet the strictest ppm was asked - and paid for in price)."""
    fields = lever_fields(case)
    combos = itertools.islice(itertools.product(*[_options(case, f) for f in fields]), MAX_COMBOS)
    best: tuple[JSONObject, float, float] | None = None
    for combo in combos:
        terms = complete_offer(case, {**base, **dict(zip(fields, combo, strict=True)), "unit_price": price})
        if not must_haves_ok(case, terms, std):
            continue
        c = safe_cost(case, terms, std, est)
        dist = _distance(terms, base, fields)
        if best is None or c < best[1] - 1.0 or (abs(c - best[1]) <= 1.0 and dist < best[2]):
            best = (terms, c, dist)
    if best is None:  # no levers (or none keeps the must-haves): price only
        terms = complete_offer(case, {**base, "unit_price": price})
        return terms, safe_cost(case, terms, std, est)
    return best[0], best[1]


def price_for_cost(case: JSONObject, terms: JSONObject, target_c: float, std: JSONObject) -> float | None:
    """The unit price at which `terms` cost `target_c` (C rises with price; bisection, 1 cent)."""
    lo, hi = 0.0, max(_num(terms.get("unit_price")) or 1.0, 1.0) * 4
    if safe_cost(case, {**terms, "unit_price": hi}, std) < target_c:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if safe_cost(case, {**terms, "unit_price": mid}, std) < target_c else (lo, mid)
        if hi - lo < 0.005:
            break
    return round(hi, 2)


def progress(case: JSONObject, events: list[Message], seconds_left: float | None) -> float:
    """How far the case is: by our messages used and, in a timed wave, by the clock."""
    limit = _num(case.get("round_limit")) or 10.0
    sent = sum(m.get("from") == "buyer" for m in events)
    turn_p = sent / max(limit - 2, 1)
    time_p = 0.0 if seconds_left is None else 1 - (seconds_left - CLOSE_S) / (FULL_WAVE_S - CLOSE_S)
    return round(min(1.0, max(0.0, turn_p, time_p)), 3)


def _relationship_target(
    case: JSONObject,
    base: JSONObject,
    price: float,
    floor: float | None,
    std: JSONObject,
    est: SupplierEstimate,
    p: float,
    proto: Protocol,
    aggr: float = 1.0,
) -> tuple[float, JSONObject, float]:
    """Price grid search for the lowest true C (price saving vs. supplier-health charge), never
    below the supplier's estimated floor: a price it cannot accept is no target at all."""
    search = config()["relationship_price_search"]
    low = max(price * search["low_pct_of_offer"] / 100, min(floor or 0.0, price))
    steps = max(search["steps"], 10)
    grid = [low + (price - low) * i / steps for i in range(steps + 1)]
    best_p, best_terms, best_c = price, base, math.inf
    for cand in grid:
        terms, c = best_package(case, base, round(cand, 2), std, est)
        if c < best_c:
            best_p, best_terms, best_c = round(cand, 2), terms, c
    anchor = proto["segment"].get("anchor_below_target_pct", 0.0) * aggr
    ask = round(best_p * (1 - anchor / 100 * (1 - p)), 2)  # start a little below, land on it
    terms, c = best_package(case, best_terms, ask, std, est)
    return ask, terms, c


def _leverage_target(
    case: JSONObject,
    base: JSONObject,
    price: float,
    floor: float | None,
    std: JSONObject,
    p: float,
    proto: Protocol,
    aggr: float = 1.0,
    soften: float = 0.0,
) -> tuple[float, JSONObject, float]:
    """Anchor -> landing curve. `aggr` scales the anchor depth by our leverage position;
    `soften` (vulnerable) lands that many % less deep."""
    seg = proto["segment"]
    if floor is not None:
        anchor = floor * (1 - seg.get("anchor_below_floor_pct", 0.0) * aggr / 100)
        landing = floor * (1 + (seg.get("landing_above_floor_pct", 0.0) + soften) / 100)
    else:
        anchor = price * (1 - seg.get("anchor_below_offer_pct", 5.0) * aggr / 100)
        landing = price * (1 - max(seg.get("landing_below_offer_pct", 1.0) - soften, 0.0) / 100)
    ask = round(min(price, anchor + (landing - anchor) * p), 2)
    terms, c = best_package(case, base, ask, std, None)
    return ask, terms, c


def thread_envelope(
    case: JSONObject,
    supplier_id: str,
    events: list[Message],
    proto: Protocol,
    pkg: Package | None,
    country: str | None,
    p: float,
    position: Position = "balanced",
) -> ThreadEnvelope:
    lev = config()["leverage"]
    hold = config()["pacing"]["hold_until_progress"]
    p = 0.0 if p < hold else (p - hold) / max(1.0 - hold, 1e-9)  # v3: no concessions while holding
    aggr = lev["aggressiveness"].get(position, 1.0)
    soften = lev["vulnerable_landing_pct"] if position == "vulnerable" else 0.0
    std = standard_terms(events)
    relationship = is_relationship_case(case, proto)
    est, ref = estimate_supplier(case, pkg, supplier_id, country, std) if relationship or pkg else (None, None)
    est_for_c = est if relationship else None
    # Suppliers often send alternatives next to their main sheet ('offer:...-a'). All are priced
    # for Claude (who can propose an alternative back), but only the main sheet can be accepted
    # (run 2: accepting an alternative got 422 "not a standing offer"), so it stays the standing one.
    offers: list[OfferOption] = []
    for oid, oterms in latest_sheets(events):
        if _num(oterms.get("unit_price")) is None:
            continue
        c_o = safe_cost(case, oterms, std)
        c_o_true = safe_cost(case, oterms, std, est_for_c)
        cov, unc = coverage(case, oterms, std)
        offers.append(
            {
                "sheet_id": oid,
                "terms": oterms,
                "c": _finite(c_o),
                "c_true": _finite(c_o_true),
                "coverage_pct": cov,
                "uncovered_eur": unc,
            }
        )
    sheet_id, terms = standing(events)
    price = _num(terms.get("unit_price"))
    sheets = [t for _, t in supplier_sheets(events) if _num(t.get("unit_price")) is not None]
    c_plain = safe_cost(case, terms, std) if price is not None else math.inf
    c_true = safe_cost(case, terms, std, est_for_c) if price is not None else math.inf
    cov_s, unc_s = coverage(case, terms, std) if terms else (None, None)

    floor: float | None = None
    if est is not None:
        seg = proto["segment"]
        if relationship:
            buyer = case.get("buyer")
            sust = _num(buyer.get("sustainable_margin_pct")) if isinstance(buyer, dict) else None
            floor = est["full_cost"] / (1 - (sust or 0.0) / 100)
        else:
            floor = est["full_cost"] * (1 + seg.get("min_margin_pct", 3.0) / 100)
        floor = round(floor, 2)

    target_price: float | None = None
    target_terms: JSONObject | None = None
    c_target: float | None = None
    c_floor: float | None = None
    if price is not None:
        base = complete_offer(case, terms)
        if relationship and est is not None:
            target_price, target_terms, ct = _relationship_target(case, base, price, floor, std, est, p, proto, aggr)
        else:
            target_price, target_terms, ct = _leverage_target(case, base, price, floor, std, p, proto, aggr, soften)
        cap = proto["segment"].get("max_discount_from_offer_pct")
        if cap is not None and target_price is not None and target_price < price * (1 - cap / 100):
            # bottleneck / strategic suppliers hold the power: an ask far below their offer makes
            # them walk (P10 in the first practice run), whatever our should-cost says
            target_price = round(price * (1 - cap / 100), 2)
            target_terms, ct = best_package(case, target_terms or base, target_price, std, est_for_c)
        c_target = _finite(ct)
        if floor is not None:
            c_floor = _finite(best_package(case, base, floor, std, est_for_c)[1])

    return {
        "supplier_id": supplier_id,
        "sheet_id": sheet_id,
        "standing_terms": terms,
        "standard": std,
        "standing_price": price,
        "c_standing": _finite(c_plain),
        "c_true_standing": _finite(c_true),
        "penalty_at_offer": _finite(c_true - c_plain) if math.isfinite(c_true) and math.isfinite(c_plain) else None,
        "c_opening": _finite(safe_cost(case, sheets[0], std)) if sheets else None,
        "supplier_estimate": est,
        "full_cost_ref": ref,
        "price_floor_est": floor,
        "c_floor_est": c_floor,
        "target_price": target_price,
        "target_terms": target_terms,
        "c_target": c_target,
        "levers": lever_table(case, complete_offer(case, terms), std, est_for_c) if price is not None else [],
        "offers": offers,
        "coverage_pct": cov_s,
        "uncovered_eur": unc_s,
        "target_coverage_pct": coverage(case, target_terms, std)[0] if target_terms else None,
    }


def envelope(
    case: JSONObject,
    threads: Threads,
    live: list[str],
    protocols: dict[str, Protocol],
    pkg: Package | None,
    countries: dict[str, str | None],
    seconds_left: float | None = None,
) -> Envelope:
    """The envelope of every live thread this turn."""
    per: dict[str, ThreadEnvelope] = {}
    p_all = 0.0
    c_open_v, c_alt_v = c_open(case, threads), c_alt(case)
    gap, position = leverage_position(c_open_v, c_alt_v)
    for sid in live:
        events = threads.get(sid, [])
        p = progress(case, events, seconds_left)
        p_all = max(p_all, p)
        per[sid] = thread_envelope(case, sid, events, protocols[sid], pkg, countries.get(sid), p, position)
    priced = [(e["c_true_standing"], sid) for sid, e in per.items() if e["c_true_standing"] is not None]
    return {
        "c_open": c_open_v,
        "c_alt": c_alt_v,
        "progress": p_all,
        "best_supplier": min(priced)[1] if priced else None,
        "leverage_gap_pct": gap,
        "position": position,
        "threads": per,
    }
