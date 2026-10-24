"""Typed, read-only access to the data package, on top of the kit's arena_kit.data.DataPackage.

Every row is checked against its TypedDict's columns before it is returned, so a changed package
(e.g. the Sunday release) fails loudly here instead of leaking wrong shapes into the runner.
"""

import logging
import os
import threading
from pathlib import Path
from typing import cast

from arena_kit.data import DataPackage

from .package_types import (
    CostDriver,
    IndexSeries,
    IndexValue,
    NegotiationEvent,
    NewsItem,
    PackageSupplier,
    Part,
    PriceCondition,
    Quote,
    Scorecard,
    ShouldCost,
    SupplierBundle,
    SupplierIntel,
    TriggerDocument,
)

log = logging.getLogger("hollerau.package")

DEFAULT_ROOT = "data/package"
ALL_ROWS = 100_000  # DataPackage.query caps rows at 200 by default

type SQLValue = str | int | float | None
type SQLRow = dict[str, SQLValue]


class PackageError(Exception):
    pass


def _as[T](kind: type[T], row: SQLRow) -> T:
    """Check `row` has exactly the TypedDict's columns, then type it."""
    expected = set(kind.__annotations__)
    if "class_" in expected and "class" in row:  # `class` is a Python keyword
        row = {("class_" if k == "class" else k): v for k, v in row.items()}
    if set(row) != expected:
        raise PackageError(f"{kind.__name__}: columns {sorted(set(row) ^ expected)} differ from the package")
    return cast(T, row)


class Package:
    def __init__(self, root: str | None = None) -> None:
        path = Path(root or os.environ.get("ARENA_DATA") or DEFAULT_ROOT)
        try:
            self.data = DataPackage(path)  # type: ignore[no-untyped-call]  # upstream is unannotated
        except FileNotFoundError as e:
            raise PackageError(f"no data package at {path} - run `uv run arena data`") from e
        # Parallel cases share one SQLite connection: serialise access, and build the kit's lazy
        # ID index now - built concurrently by several threads it breaks (seen in the rehearsal).
        self.lock = threading.RLock()
        with self.lock:
            self.data.lookup("")  # type: ignore[no-untyped-call]

    def _query(self, sql: str, params: tuple[SQLValue, ...] = ()) -> list[SQLRow]:
        try:
            with self.lock:
                rows = self.data.query(sql, params, limit=ALL_ROWS)  # type: ignore[no-untyped-call]
        except Exception as e:  # sqlite3 errors, read-only guard
            log.error("package query failed: %s", e)
            raise PackageError(f"{type(e).__name__}: {e}") from e
        return cast(list[SQLRow], rows)

    def _one[T](self, kind: type[T], sql: str, params: tuple[SQLValue, ...]) -> T | None:
        rows = self._query(sql, params)
        return _as(kind, rows[0]) if rows else None

    def all_suppliers(self) -> list[PackageSupplier]:
        return [_as(PackageSupplier, r) for r in self._query("SELECT * FROM suppliers ORDER BY id")]

    def supplier(self, supplier_id: str) -> PackageSupplier:
        row = self._one(PackageSupplier, "SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
        if row is None:
            raise PackageError(f"unknown supplier {supplier_id}")
        return row

    def supplier_bundle(self, supplier_id: str, part_id: str | None) -> SupplierBundle:
        return {
            "supplier": self.supplier(supplier_id),
            "intel": self._one(SupplierIntel, "SELECT * FROM supplier_intel WHERE supplier_id = ?", (supplier_id,)),
            "part": self._one(Part, "SELECT * FROM parts WHERE id = ?", (part_id,)) if part_id else None,
            "current_price": self._one(
                PriceCondition,
                "SELECT * FROM price_conditions WHERE supplier_id = ? AND part_id = ? ORDER BY valid_from DESC LIMIT 1",
                (supplier_id, part_id),
            )
            if part_id
            else None,
            "latest_scorecard": self._one(
                Scorecard,
                "SELECT * FROM scorecards WHERE supplier_id = ? ORDER BY quarter DESC LIMIT 1",
                (supplier_id,),
            ),
            "negotiation_history": [
                _as(NegotiationEvent, r)
                for r in self._query(
                    "SELECT * FROM negotiation_history WHERE supplier_id = ? ORDER BY date", (supplier_id,)
                )
            ],
        }

    def trigger_document(self, doc_id: str) -> TriggerDocument:
        rows = self._query("SELECT * FROM documents WHERE id = ?", (doc_id,))
        if not rows:
            raise PackageError(f"unknown document {doc_id}")
        try:
            with self.lock:
                text = str(self.data.document(doc_id))  # type: ignore[no-untyped-call]
        except FileNotFoundError as e:
            raise PackageError(f"document file for {doc_id} missing") from e
        return _as(TriggerDocument, {**rows[0], "text": text})

    def should_cost(self, part_id: str, supplier_id: str | None) -> ShouldCost | None:
        """The category team's full-cost estimate: this supplier's own plant if modelled, else the
        generic (German cost base) row for the part."""
        rows = [_as(ShouldCost, r) for r in self._query("SELECT * FROM should_cost WHERE part_id = ?", (part_id,))]
        own = [r for r in rows if supplier_id and r["supplier_id"] == supplier_id]
        generic = [r for r in rows if r["supplier_id"] is None]
        found = own or generic
        return found[0] if found else None

    def cost_drivers(self, part_id: str) -> list[CostDriver]:
        rows = self._query("SELECT * FROM cost_drivers WHERE part_id = ? ORDER BY weight DESC", (part_id,))
        return [_as(CostDriver, r) for r in rows]

    def index_series(self, series_id: str) -> IndexSeries | None:
        return self._one(IndexSeries, "SELECT * FROM index_series WHERE id = ?", (series_id,))

    def index_values(self, series_id: str) -> list[IndexValue]:
        rows = self._query("SELECT * FROM index_values WHERE series_id = ? ORDER BY month", (series_id,))
        return [_as(IndexValue, r) for r in rows]

    def quotes(self, part_id: str) -> list[Quote]:
        """Every quotation for the part, newest first (this supplier's own and rivals')."""
        rows = self._query("SELECT * FROM quotes WHERE part_id = ? ORDER BY quote_date DESC", (part_id,))
        return [_as(Quote, r) for r in rows]

    def latest_quote_date(self) -> str | None:
        """The newest quotation date in the whole package - the data's 'today' for quote age."""
        rows = self._query("SELECT MAX(quote_date) AS d FROM quotes")
        value = rows[0]["d"] if rows else None
        return value if isinstance(value, str) else None

    def news(self, supplier_id: str) -> list[NewsItem]:
        rows = self._query("SELECT * FROM news WHERE supplier_id = ? ORDER BY date DESC", (supplier_id,))
        return [_as(NewsItem, r) for r in rows]

    def is_citable(self, ref: str) -> bool:
        """True if the arena knows this ID (facts.json or a table row) - unknown IDs cost trust."""
        with self.lock:
            return self.data.lookup(ref) is not None  # type: ignore[no-untyped-call]
