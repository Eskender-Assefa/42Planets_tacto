"""Checked claims, one per message - the winners' evidence pattern (docs/winners_analysis).

The arena reads every data ID in an e-mail and checks the figure in the same sentence against
facts.json (brief/api.md, "What counts"). In the EHL final the winning agent cited exactly one new
verified claim per message: suppliers conceded ~2.3 % after such a message and ~0.3 % after one
without, and three claims in one message moved them only ~5 %. Our practice replays had 12 of 18
claims 'irrelevant' (own offer cited as a rival, other cases' quotes) and no index claim at all
(the model kept one of the two idx IDs a window needs).

So Python writes the claim sentences here, every figure copied from the facts the arena checks
against, and attaches one per outgoing offer, strongest first. Rules followed:
- idx: two months of one series, at most 12 months apart, ending within the last 12 months of the
  index data as a whole (not of the series); the most favourable such window of the part's own
  cost drivers. Live check post-winners: the energy index (PPI-D351) on parts it does not drive and
  a window ending 2025-09 (data to 2026-09) came back 'irrelevant'; driver windows ending 2025-10
  were verified
- quote / offer: only another supplier's live offer in this session (RFQ), and only when cheaper
- doc + ctr: the notice the supplier's letter gives against the contract's notice
- fc: the recorded forecast change; sc: on-time % (quality cases: ppm); cost: the full-cost estimate
- po: 2-8 order lines of the same part
Each ID counts once per case, so a claim whose IDs were cited already is skipped.
Figures carry no thousands separator: the arena read "2,376 ppm" as 2.376 -> 'contradicted' (live
full run, P11: the supplier added EUR 3.00 for the lost trust; EHL sellm lost H07 the same way).
"""

import logging
from collections.abc import Callable
from typing import TypedDict

from .kit import JSONObject, JSONValue
from .package import Package, PackageError

log = logging.getLogger("hollerau.claims")

MAX_WINDOW_MONTHS = 12
RECENT_MONTHS = 11  # window end at most this many months before the newest month of all index data
MIN_INDEX_FALL_PCT = 1.0  # a smaller fall is not worth a round ("a drop in the bucket")
OTD_WEAK_PCT = 95.0
PO_LINES = 3


class Claim(TypedDict):
    kind: str  # 'index' | 'notice' | 'should_cost' | 'volume' | 'delivery' | 'quality' | 'history' | 'rival_offer'
    sentence: str
    refs: list[str]
    price: float | None  # a cited EUR figure judged against the live offer per turn (None: always favourable)


def _months(month: str) -> int:
    return int(month[:4]) * 12 + int(month[5:7]) - 1


def _fact(pkg: Package, case: JSONObject, ref: str) -> dict[str, JSONValue] | None:
    """The fact the arena checks a citation against: the case's own facts first, then the package."""
    own = case.get("facts")
    if isinstance(own, dict) and isinstance(own.get(ref), dict):
        return own[ref]  # type: ignore[return-value]
    with pkg.lock:
        got = pkg.data.facts.get(ref)
    return got if isinstance(got, dict) else None


def _num(v: JSONValue | None) -> float | None:
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) else None


def data_last_month(pkg: Package) -> str | None:
    """The newest month of the index data as a whole - 'the data' the arena's recency rule means."""
    rows = pkg._query("SELECT MAX(month) AS m FROM index_values")
    value = rows[0]["m"] if rows else None
    return value if isinstance(value, str) else None


def best_index_window(pkg: Package, series_id: str, data_last: str | None = None) -> tuple[float, str, str] | None:
    """(change %, earlier id, later id) of the most negative valid window of one series."""
    values = [v for v in pkg.index_values(series_id) if v["value"]]
    if len(values) < 2:
        return None
    last = _months(data_last or values[-1]["month"])
    best: tuple[float, str, str] | None = None
    for j, b in enumerate(values):
        if _months(b["month"]) < last - RECENT_MONTHS:
            continue
        for a in values[:j]:
            gap = _months(b["month"]) - _months(a["month"])
            if not 1 <= gap <= MAX_WINDOW_MONTHS or not a["value"] or b["value"] is None:
                continue
            change = (b["value"] / a["value"] - 1) * 100
            if best is None or change < best[0]:
                best = (change, a["id"], b["id"])
    return best


def _index_claims(pkg: Package, case: JSONObject, part_id: str) -> list[Claim]:
    series = [d["series_id"] for d in pkg.cost_drivers(part_id)]  # only the part's drivers are relevant
    data_last = data_last_month(pkg)
    found: list[tuple[float, Claim]] = []
    for sid in series:
        got = best_index_window(pkg, sid, data_last)
        if got is None:
            continue
        change, a, b = got
        fa, fb = _fact(pkg, case, a), _fact(pkg, case, b)
        va, vb = (_num(fa.get("value")) if fa else None), (_num(fb.get("value")) if fb else None)
        if va is None or vb is None or not va:
            continue
        change = round((vb / va - 1) * 100, 1)  # the arena's figure, from the facts it checks against
        if change > -MIN_INDEX_FALL_PCT:
            continue  # only a clear fall argues for us
        sentence = f"The index {sid} changed {change:+.1f} % from {a.split('@')[1]} to {b.split('@')[1]} ({a}, {b})."
        found.append((change, {"kind": "index", "sentence": sentence, "refs": [a, b], "price": None}))
    found.sort(key=lambda x: x[0])
    return [c for _, c in found[:2]]


def _notice_claim(pkg: Package, case: JSONObject, supplier_id: str) -> Claim | None:
    trigger, refs = case.get("trigger_doc"), case.get("refs")
    if not isinstance(trigger, str):
        return None
    doc = _fact(pkg, case, trigger)
    days = _num(doc.get("days")) if doc else None
    if days is None or doc is None or doc.get("supplier") != supplier_id:
        return None
    ctrs = [r for r in refs if isinstance(r, str) and r.startswith("ctr:")] if isinstance(refs, list) else []
    ctrs += [k for k, _ in _case_facts(case, "ctr:", supplier=supplier_id) if k not in ctrs]
    for ctr in ctrs:
        fact = _fact(pkg, case, ctr)
        need = _num(fact.get("days")) if fact else None
        if fact is None or need is None or fact.get("supplier") != supplier_id or days >= need:
            continue
        sentence = (
            f"Your letter {trigger} gives us {days:.0f} days of notice, while our agreement {ctr} "
            f"requires {need:.0f} days."
        )
        return {"kind": "notice", "sentence": sentence, "refs": [trigger, ctr], "price": None}
    return None


def _should_cost_claim(pkg: Package, case: JSONObject, part_id: str, supplier_id: str) -> Claim | None:
    in_case = _case_facts(case, "cost:", part=part_id)
    if in_case:
        ref, fact = in_case[-1]
        cost = _num(fact.get("unit_cost"))
    else:
        sc = pkg.should_cost(part_id, supplier_id)
        ref, cost = (sc["id"], sc["unit_cost"]) if sc else ("", None)
    if cost is None or not ref:
        return None
    sentence = f"Our bottom-up estimate of the full cost is EUR {cost:.2f} per unit before margin ({ref})."
    return {"kind": "should_cost", "sentence": sentence, "refs": [ref], "price": float(cost)}


def _volume_claim(pkg: Package, case: JSONObject, part_id: str) -> Claim | None:
    in_case = _case_facts(case, "fc:", part=part_id)
    if in_case:
        ref: JSONValue = in_case[-1][0]
    else:
        rows = pkg._query("SELECT id FROM forecasts WHERE part_id = ? ORDER BY snapshot_month DESC LIMIT 1", (part_id,))
        ref = rows[0]["id"] if rows else None
    fact = _fact(pkg, case, ref) if isinstance(ref, str) else None
    change, vol = (_num(fact.get("change_pct")), _num(fact.get("volume_per_year"))) if fact else (None, None)
    if not isinstance(ref, str) or change is None or change <= 0:
        return None  # a falling forecast argues for the supplier
    sentence = (
        f"Our forecast {ref} expects {vol:.0f} units a year, a change of {change:+.1f} %."
        if vol
        else f"Our forecast {ref} shows a change of {change:+.1f} %."
    )
    return {"kind": "volume", "sentence": sentence, "refs": [ref], "price": None}


def _case_facts(case: JSONObject, prefix: str, **match: str) -> list[tuple[str, dict[str, JSONValue]]]:
    """(id, fact) of the case's own facts with this ID prefix whose fields equal `match`, newest ID
    last. The final brings new suppliers whose records may exist only in the case file."""
    own = case.get("facts")
    if not isinstance(own, dict):
        return []
    found = [
        (k, v)
        for k, v in own.items()
        if k.startswith(prefix) and isinstance(v, dict) and all(v.get(f) == want for f, want in match.items())
    ]
    return sorted(found, key=lambda kv: kv[0])


def _scorecard_claim(pkg: Package, case: JSONObject, supplier_id: str, quality: bool) -> Claim | None:
    in_case = _case_facts(case, "sc:", supplier=supplier_id)
    if in_case:
        ref, fact = in_case[-1]
        quarter = str(fact.get("quarter") or ref.split("@")[-1])
    else:
        card = pkg.supplier_bundle(supplier_id, None)["latest_scorecard"]
        found = _fact(pkg, case, card["id"]) if card else None
        if card is None or found is None:
            return None
        ref, fact, quarter = card["id"], found, str(card["quarter"])
    if quality:
        ppm = _num(fact.get("ppm"))
        if not ppm:
            return None
        sentence = f"Your rolling twelve-month defect rate in {quarter} was {ppm:.0f} ppm ({ref})."
        return {"kind": "quality", "sentence": sentence, "refs": [ref], "price": None}
    otd = _num(fact.get("otd_pct"))
    if otd is None or otd >= OTD_WEAK_PCT:
        return None
    sentence = f"Your rolling twelve-month on-time delivery in {quarter} was {otd:.1f} % ({ref})."
    return {"kind": "delivery", "sentence": sentence, "refs": [ref], "price": None}


def _history_claim(pkg: Package, part_id: str, supplier_id: str) -> Claim | None:
    rows = pkg._query(
        "SELECT id, price FROM po_lines WHERE part_id = ? AND supplier_id = ? ORDER BY order_date DESC LIMIT ?",
        (part_id, supplier_id, PO_LINES),
    )
    prices = [_num(r["price"]) for r in rows]
    if len(rows) < 2 or any(p is None for p in prices):
        return None
    ids = [str(r["id"]) for r in rows]
    shown = sorted({p for p in prices if p is not None})
    figures = f"EUR {shown[0]:.2f}" if len(shown) == 1 else ", ".join(f"EUR {p:.2f}" for p in shown)
    sentence = f"Our last {len(rows)} orders for this part were at {figures} ({', '.join(ids)})."
    return {"kind": "history", "sentence": sentence, "refs": ids, "price": max(p for p in prices if p is not None)}


def build_claims(pkg: Package | None, case: JSONObject, supplier_id: str) -> list[Claim]:
    """The case's claim queue for one supplier, strongest first (the winners' order). Part-level
    claims need a single-part case; a bundle argues with its first part's indices."""
    if pkg is None:
        return []
    quality = case.get("type") == "quality"
    parts = case.get("parts")
    first = str(parts[0]) if isinstance(parts, list) and parts else None
    part_id = first if isinstance(parts, list) and len(parts) == 1 else None
    steps: list[Callable[[], list[Claim | None]]] = []
    if quality:
        steps.append(lambda: [_scorecard_claim(pkg, case, supplier_id, quality=True)])
    if first:
        steps.append(lambda: list(_index_claims(pkg, case, first)))
    steps.append(lambda: [_notice_claim(pkg, case, supplier_id)])
    if part_id:
        steps.append(lambda: [_should_cost_claim(pkg, case, part_id, supplier_id)])
        steps.append(lambda: [_volume_claim(pkg, case, part_id)])
    if not quality:
        steps.append(lambda: [_scorecard_claim(pkg, case, supplier_id, quality=False)])
    if part_id:
        steps.append(lambda: [_history_claim(pkg, part_id, supplier_id)])
    out: list[Claim | None] = []
    for step in steps:  # each kind on its own: a supplier new to our data must not cost the rest
        try:
            out += step()
        except (PackageError, KeyError, TypeError, ValueError) as e:
            log.warning("a claim for %s skipped: %s", supplier_id, e)
    claims = [c for c in out if c is not None]
    for c in claims:  # never an ID the arena does not know: it would be 'contradicted'
        if not all(pkg.is_citable(r) or _fact(pkg, case, r) for r in c["refs"]):
            log.warning("dropping claim with uncitable refs %s", c["refs"])
    return [c for c in claims if all(pkg.is_citable(r) or _fact(pkg, case, r) for r in c["refs"])]


def rival_offer_claim(sheet_id: str, price: float) -> Claim:
    """An RFQ rival's live offer - citable to every other bidder, once per supplier."""
    sentence = f"Another bidder in this tender currently offers EUR {price:.2f} per unit ({sheet_id})."
    return {"kind": "rival_offer", "sentence": sentence, "refs": [sheet_id], "price": price}


def favourable(claim: Claim, standing_price: float | None, factor: float) -> bool:
    """A claim with a EUR figure argues for us only when that figure is below the live offer."""
    if claim["price"] is None:
        return True
    return standing_price is not None and claim["price"] < standing_price * factor
