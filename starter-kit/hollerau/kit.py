"""Typed facade over the (unannotated) upstream arena_kit: the only place hollerau calls it untyped.

All cost arithmetic stays in arena_kit.cost.total_cost - this module only gives it types.
"""

from typing import cast

from arena_kit import cost
from arena_kit.cli import load_env as _load_env
from arena_kit.docs import standard_terms as _standard_terms
from arena_kit.play import standing as _standing

type JSONValue = str | int | float | bool | None | list[JSONValue] | dict[str, JSONValue]
type JSONObject = dict[str, JSONValue]
type Message = JSONObject  # one e-mail in a thread (supplier's or ours)
type Threads = dict[str, list[Message]]  # supplier_id -> messages, oldest first


def load_env() -> None:
    _load_env()  # type: ignore[no-untyped-call]


def total_cost(case: JSONObject, terms: JSONObject, standard: JSONObject | None = None) -> float:
    return float(cost.total_cost(case, terms, standard))  # type: ignore[no-untyped-call]


def standing(events: list[Message]) -> tuple[str | None, JSONObject]:
    """(term_sheet_id, terms) of the supplier's standing term sheet in a thread, or (None, {})."""
    sheet_id, terms = _standing(events)  # type: ignore[no-untyped-call]
    return (str(sheet_id) if sheet_id else None), cast(JSONObject, terms)


def standard_terms(events: list[Message]) -> JSONObject:
    return cast(JSONObject, _standard_terms(events))  # type: ignore[no-untyped-call]
