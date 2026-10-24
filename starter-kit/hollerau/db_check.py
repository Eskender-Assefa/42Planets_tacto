"""Verify the Supabase schema end to end: write, read back, reject a duplicate move, clean up.

    cd starter-kit && uv run python -m hollerau.db_check

Uses throwaway ids (prefix 'selftest-') and deletes everything it wrote, even on failure.
If SUPABASE_ANON_KEY is set, also checks the dashboard's key can read but not write.
"""

import logging
import os
import sys
import uuid

from arena_kit.cli import load_env

from .db import DBError, SupabaseDB
from .types import AuditLogRow, CaseRow, SupplierRow

log = logging.getLogger("hollerau.db_check")


def ok(msg: str) -> None:
    print(f"  ok  {msg}")


def check_service_role(db: SupabaseDB, session_id: str, supplier_id: str) -> None:
    supplier: SupplierRow = {"id": supplier_id, "name": "Selftest GmbH", "country": "DE",
                             "category": "castings", "abc_class": "C"}  # fmt: skip
    db.upsert_suppliers([supplier])
    ok("upsert supplier")

    case: CaseRow = {"session_id": session_id, "case_id": "case:SELFTEST", "environment": "sim",
                     "title": "db_check", "category_goal": "leverage", "c_open": 1000.0,
                     "supplier_ids": [supplier_id]}  # fmt: skip
    written = db.upsert_case(case)
    if written.get("status") != "active":
        raise DBError(f"case default status not applied: {written.get('status')!r}")
    ok("insert case (default status = active)")

    audit: AuditLogRow = {
        "session_id": session_id,
        "supplier_id": supplier_id,
        "turn_number": 1,
        "action": "send",
        "seconds_left": 420,
        "supplier_terms": {"unit_price": 16.59, "payment_days": 60},
        "proposed_terms": {"unit_price": 15.9, "payment_days": 30},
        "c_supplier_offer": 112451.5,
        "c_proposed": 108000.0,
        "observed_barrier": "selftest",
        "strategic_intent": "selftest",
        "mathematical_justification": "selftest",
        "message_body": "selftest",
        "c_target": 105000.0,
        "c_floor_est": 101000.0,
        "decision_source": "naive",
        "claims": {"verified": 1, "irrelevant": 0, "contradicted": 0, "duplicate": 0},
    }
    row = db.insert_audit(audit)
    ok(f"insert audit row (id={row.get('id')})")

    back = db.select("audit_logs", session_id=f"eq.{session_id}")
    if len(back) != 1 or back[0].get("proposed_terms") != audit["proposed_terms"]:
        raise DBError(f"read-back mismatch: {back!r}")
    ok("read back audit row, JSON terms intact")

    try:
        db.insert_audit(audit)
    except DBError as e:
        if e.status != 409:
            raise
        ok("duplicate move rejected (409)")
    else:
        raise DBError("duplicate move was accepted - unique constraint missing")

    scores = db.select("wave_scores", environment="eq.sim")
    ok(f"wave_scores view readable ({len(scores)} row(s))")

    overview = db.select("case_overview", session_id=f"eq.{session_id}")
    if len(overview) != 1:
        raise DBError(f"case_overview returned {len(overview)} rows - run db/migrations/002_case_overview.sql")
    o = overview[0]
    if o.get("moves") != 1 or o.get("last_seconds_left") != 420 or o.get("supplier_ids") != [supplier_id]:
        raise DBError(f"case_overview live state wrong: {o!r}")
    ok("case_overview shows the latest move (moves=1, last_seconds_left=420)")
    if o.get("last_c_target") != 105000.0 or o.get("last_decision_source") != "naive":
        raise DBError(f"telemetry columns missing - run db/migrations/003_agent_telemetry.sql: {o!r}")
    ok("migration 003 telemetry columns present (c_target, decision_source, claims)")


def check_anon(url: str, anon_key: str, session_id: str) -> None:
    anon = SupabaseDB(url, anon_key)
    try:
        if not anon.select("cases", session_id=f"eq.{session_id}"):
            raise DBError("anon key cannot read cases - check the read policies")
        ok("anon key can read")
        try:
            anon.upsert_case({"session_id": f"{session_id}-anon", "case_id": "x", "environment": "sim"})
        except DBError as e:
            if e.status not in (401, 403):
                raise
            ok(f"anon key cannot write ({e.status})")
        else:
            raise DBError("anon key could write to cases - RLS is not enabled")
    finally:
        anon.close()


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    load_env()  # type: ignore[no-untyped-call]  # upstream arena_kit is unannotated
    session_id = f"selftest-{uuid.uuid4().hex[:8]}"
    supplier_id = "sup:selftest"
    try:
        db = SupabaseDB()
    except DBError as e:
        print(f"FAIL {e}")
        return 1
    print(f"Supabase check against {os.environ['SUPABASE_URL']}")
    failed = False
    try:
        check_service_role(db, session_id, supplier_id)
        anon_key = os.environ.get("SUPABASE_ANON_KEY")
        if anon_key:
            check_anon(os.environ["SUPABASE_URL"], anon_key, session_id)
        else:
            print("  --  SUPABASE_ANON_KEY not set: skipped the dashboard read/write check")
    except DBError as e:
        print(f"FAIL {e}")
        failed = True
    finally:
        try:
            db.delete("cases", session_id="like.selftest-%")  # cascades to audit_logs
            db.delete("suppliers", id=f"eq.{supplier_id}")
            ok("cleaned up test rows")
        except DBError as e:
            print(f"WARN cleanup failed: {e}")
        db.close()
    print("FAILED" if failed else "ALL CHECKS PASSED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
