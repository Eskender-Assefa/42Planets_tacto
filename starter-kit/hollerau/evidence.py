"""Pre-session research: data-backed arguments as ready-to-cite sentences.

Every figure is computed here in Python (never by the model) and every ID is checked against the
package, because the arena verifies cited figures (`claim_results`) and an unknown or wrong one
costs trust. Index windows follow the kit's README: two months of one series, at most 12 months
apart, ending within the last 12 months of the data.
"""

import logging
from typing import NotRequired, TypedDict

from .package import Package, PackageError

log = logging.getLogger("hollerau.evidence")

WINDOW_MONTHS = 12
QUOTES_PER_KIND = 2


class Evidence(TypedDict):
    kind: (
        str  # 'index' | 'index_basket' | 'scorecard' | 'should_cost' | 'own_quote' | 'rival_quote' | 'news' | 'history'
    )
    sentence: str
    refs: list[str]  # citable IDs in the sentence (empty: context only, do not cite)
    favourable: bool  # supports a lower price / better terms for us
    price: NotRequired[float | None]  # quotes / should-cost: judged against the live offer per turn


class Brief(TypedDict):
    supplier_id: str
    part_id: str | None
    asked_pct: float | None  # the increase the trigger letter asks for, if any
    index_justified_pct: float | None  # weighted driver change: what the indices support
    items: list[Evidence]


def _month_minus(month: str, n: int) -> str:
    y, m = int(month[:4]), int(month[5:7])
    total = y * 12 + (m - 1) - n
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _index_change(pkg: Package, series_id: str) -> tuple[float, str, str, str] | None:
    """(change %, sentence, base id, last id) over the latest 12-month window."""
    values = [v for v in pkg.index_values(series_id) if v["value"] is not None]
    if len(values) < 2:
        return None
    last = values[-1]
    floor = _month_minus(last["month"], WINDOW_MONTHS)
    window = [v for v in values if v["month"] >= floor]
    base = window[0]
    if base["id"] == last["id"] or not base["value"] or last["value"] is None:
        return None
    change = (last["value"] / base["value"] - 1) * 100
    series = pkg.index_series(series_id)
    name = (series["name"] if series else None) or series_id
    sentence = f"{name} changed {change:+.1f}% from {base['month']} to {last['month']} ({base['id']}, {last['id']})."
    return change, sentence, base["id"], last["id"]


def build_brief(pkg: Package, supplier_id: str, part_id: str | None, asked_pct: float | None) -> Brief:
    items: list[Evidence] = []
    justified: float | None = None
    try:
        if part_id:
            weighted, weights = 0.0, 0.0
            for d in pkg.cost_drivers(part_id):
                got = _index_change(pkg, d["series_id"])
                if got is None or d["weight"] is None:
                    continue
                change, sentence, a, b = got
                weighted += d["weight"] * change
                weights += d["weight"]
                # for us only if the driver fell, or rose less than the increase asked for
                fav = change <= 0 if asked_pct is None else change < asked_pct
                items.append({"kind": "index", "sentence": sentence, "refs": [a, b], "favourable": fav})
            if weights:
                justified = round(weighted, 2)  # share-weighted: drivers cover `weights` of the cost
                items.append(
                    {
                        "kind": "index_basket",
                        "sentence": (
                            f"Weighted by this part's cost drivers ({weights:.0%} of its cost), the indices "
                            f"support a price change of {justified:+.1f}%"
                            + (f", against the {asked_pct:.1f}% you ask." if asked_pct is not None else ".")
                        ),
                        "refs": [],
                        "favourable": justified <= 0 if asked_pct is None else justified < asked_pct,
                    }
                )
            sc = pkg.should_cost(part_id, supplier_id)
            if sc and sc["unit_cost"] is not None:
                items.append(
                    {
                        "kind": "should_cost",
                        "sentence": f"Our cost model puts the full cost at EUR {sc['unit_cost']:,.2f} ({sc['id']}).",
                        "refs": [sc["id"]],
                        "favourable": False,  # decided per turn against the offer by the negotiator
                        "price": sc["unit_cost"],
                    }
                )
        if part_id:  # quotations for the same part: its own earlier price and rivals' prices
            all_quotes = [q for q in pkg.quotes(part_id) if q["unit_price"] is not None and q["quote_date"]]
            newest = max((q["quote_date"] or "" for q in all_quotes), default="")
            cutoff = f"{int(newest[:4]) - 1}{newest[4:]}" if newest else ""
            quotes = [q for q in all_quotes if (q["quote_date"] or "") >= cutoff]  # stale quotes read as irrelevant
            own = [q for q in quotes if q["supplier_id"] == supplier_id][:QUOTES_PER_KIND]
            rivals = [q for q in quotes if q["supplier_id"] != supplier_id][:QUOTES_PER_KIND]
            for q in own:
                items.append(
                    {
                        "kind": "own_quote",
                        "sentence": (
                            f"Your quotation of {q['quote_date']} was EUR {q['unit_price']:,.2f} per unit ({q['id']})."
                        ),
                        "refs": [q["id"]],
                        "favourable": False,  # decided per turn against the offer by the negotiator
                        "price": q["unit_price"],
                    }
                )
            for q in rivals:
                items.append(
                    {
                        "kind": "rival_quote",
                        "sentence": (
                            f"A qualified quotation of {q['quote_date']} offers EUR {q['unit_price']:,.2f} "
                            f"per unit ({q['id']})."
                        ),
                        "refs": [q["id"]],
                        "favourable": False,
                        "price": q["unit_price"],
                    }
                )
        bundle = pkg.supplier_bundle(supplier_id, part_id)
        card = bundle["latest_scorecard"]
        if card and card["otd_pct"] is not None:
            items.append(
                {
                    "kind": "scorecard",
                    "sentence": (
                        f"Your delivery reliability was {card['otd_pct']:.1f}% on time with {card['ppm'] or 0} ppm "
                        f"in {card['quarter']} (class {card['class_']}, {card['id']})."
                    ),
                    "refs": [card["id"]],
                    "favourable": card["colour"] in ("amber", "red"),
                }
            )
        for ev in bundle["negotiation_history"][-3:]:
            if ev["asked_pct"] is not None and ev["settled_pct"] is not None:
                items.append(
                    {
                        "kind": "history",
                        "sentence": (
                            f"{ev['date']}: {ev['type']} - asked {ev['asked_pct']:.1f}%, settled at "
                            f"{ev['settled_pct']:.1f}%."
                        ),
                        "refs": [],  # history events carry no citable ID: context only
                        "favourable": ev["settled_pct"] < ev["asked_pct"],
                    }
                )
        for n in pkg.news(supplier_id)[:3]:
            items.append(
                {
                    "kind": "news",
                    "sentence": f"{n['date']}: {n['headline']} ({n['id']}).",
                    "refs": [n["id"]],
                    "favourable": False,  # the model judges relevance from the headline
                }
            )
    except PackageError as e:
        log.warning("brief for %s incomplete: %s", supplier_id, e)

    for item in items:  # never hand the model an ID the arena would not know
        bad = [r for r in item["refs"] if not pkg.is_citable(r)]
        if bad:
            log.warning("dropping uncitable refs %s", bad)
            item["refs"] = [r for r in item["refs"] if r not in bad]
    return {
        "supplier_id": supplier_id,
        "part_id": part_id,
        "asked_pct": asked_pct,
        "index_justified_pct": justified,
        "items": items,
    }
