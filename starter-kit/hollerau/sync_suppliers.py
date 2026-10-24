"""Mirror the package's supplier master (world.sqlite `suppliers`) into Supabase. Idempotent.

cd starter-kit && uv run python -m hollerau.sync_suppliers
"""

import logging
import sys

from arena_kit.cli import load_env

from .db import DBError, SupabaseDB
from .package import Package, PackageError
from .types import SupplierRow

log = logging.getLogger("hollerau.sync_suppliers")

BATCH = 200


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    load_env()  # type: ignore[no-untyped-call]  # upstream arena_kit is unannotated
    try:
        rows: list[SupplierRow] = [
            {
                "id": s["id"],
                "name": s["name"],
                "country": s["country"],
                "category": s["category"],
                "abc_class": s["abc_class"],
            }  # fmt: skip
            for s in Package().all_suppliers()
        ]
        db = SupabaseDB()
    except (PackageError, DBError) as e:
        print(f"FAIL {e}")
        return 1
    try:
        written = 0
        for i in range(0, len(rows), BATCH):
            written += len(db.upsert_suppliers(rows[i : i + BATCH]))
        stored = len(db.select("suppliers"))
    except DBError as e:
        print(f"FAIL {e}")
        return 1
    finally:
        db.close()
    print(f"package suppliers: {len(rows)}, upserted: {written}, now in Supabase: {stored}")
    return 0 if stored >= len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
