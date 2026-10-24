"""Typed facade over the (unannotated) upstream arena_kit: the only place hollerau calls it untyped.

All cost arithmetic stays in arena_kit.cost - this module only gives it types.
"""

from typing import TypedDict, cast

from arena_kit import cost
from arena_kit.cli import load_env as _load_env
from arena_kit.docs import standard_terms as _standard_terms
from arena_kit.play import closing_move as _closing_move
from arena_kit.play import latest as _latest
from arena_kit.play import live_threads as _live_threads
from arena_kit.play import moves_left as _moves_left
from arena_kit.play import standing as _standing

type JSONValue = str | int | float | bool | None | list[JSONValue] | dict[str, JSONValue]
type JSONObject = dict[str, JSONValue]
type Message = JSONObject  # one e-mail in a thread (supplier's or ours)
type Threads = dict[str, list[Message]]  # supplier_id -> messages, oldest first


class SupplierEstimate(TypedDict):
    """Our estimate of a supplier for the relationship term (arena_kit.cost.supplier_value)."""

    full_cost: float  # EUR per unit, the supplier's full cost without margin
    interest_rate: float  # what money is worth to it per year
    standard: JSONObject  # its standard terms (quote PDF), gaps filled from the case


def load_env() -> None:
    _load_env()  # type: ignore[no-untyped-call]


def total_cost(
    case: JSONObject,
    terms: JSONObject,
    standard: JSONObject | None = None,
    supplier: SupplierEstimate | None = None,
) -> float:
    """C in EUR (inf for a sheet without price). With `supplier`, stabilise / secure_supply cases
    include the charge for leaving the supplier below its sustainable margin."""
    return float(cost.total_cost(case, terms, standard, supplier))  # type: ignore[no-untyped-call]


def relationship_cost(
    case: JSONObject, terms: JSONObject, standard: JSONObject | None, supplier: SupplierEstimate
) -> float:
    return float(cost.relationship_cost(case, terms, standard, supplier))  # type: ignore[no-untyped-call]


def cost_breakdown(
    case: JSONObject, terms: JSONObject, standard: JSONObject | None = None, supplier: SupplierEstimate | None = None
) -> dict[str, float]:
    """C by component (price, uncovered_need, fallback_risk, payment_terms, ...)."""
    parts = cost.cost_breakdown(case, terms, standard, supplier)  # type: ignore[no-untyped-call]
    return {str(k): float(v) for k, v in parts.items()}


def closing_terms(case: JSONObject, terms: JSONObject, standard: JSONObject | None = None) -> JSONObject:
    return cast(JSONObject, cost.closing_terms(case, terms, standard))  # type: ignore[no-untyped-call]


def complete_offer(case: JSONObject, terms: JSONObject) -> JSONObject:
    """A valid term sheet: exactly the negotiable fields, snapped to the allowed options."""
    return cast(JSONObject, cost.complete_offer(case, terms))  # type: ignore[no-untyped-call]


def must_haves_ok(case: JSONObject, terms: JSONObject, standard: JSONObject | None = None) -> bool:
    return bool(cost.must_haves_ok(case, terms, standard))  # type: ignore[no-untyped-call]


def standing(events: list[Message]) -> tuple[str | None, JSONObject]:
    """(term_sheet_id, terms) of the supplier's standing term sheet in a thread, or (None, {})."""
    sheet_id, terms = _standing(events)  # type: ignore[no-untyped-call]
    return (str(sheet_id) if sheet_id else None), cast(JSONObject, terms)


def standard_terms(events: list[Message]) -> JSONObject:
    return cast(JSONObject, _standard_terms(events))  # type: ignore[no-untyped-call]


def latest(events: list[Message]) -> Message:
    """The supplier's latest message in a thread."""
    return cast(Message, _latest(events))  # type: ignore[no-untyped-call]


def live_threads(threads: Threads) -> list[str]:
    return [str(s) for s in _live_threads(threads)]  # type: ignore[no-untyped-call]


def moves_left(case: JSONObject, events: list[Message]) -> int:
    return int(_moves_left(case, events))  # type: ignore[no-untyped-call]


def closing_move(case: JSONObject, threads: Threads) -> JSONObject:
    """Accept the cheapest standing sheet that keeps the must-haves and beats the alternative, else
    walk away - the kit's time-cap move."""
    return cast(JSONObject, _closing_move(case, threads))  # type: ignore[no-untyped-call]
