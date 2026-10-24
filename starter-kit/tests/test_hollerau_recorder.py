"""RecordingTable: a stale offer must not cost the whole case (practice, factors run: P05)."""

import pytest

from arena_kit.client import ArenaError
from hollerau.recorder import RecordingTable


class StandInArena:
    """The arena refuses the accept: the offer stopped standing (the thread closed silently)."""

    def send_message(self, session_id, supplier_id, message):
        raise ArenaError(422, "not a standing offer in this session")


class StandInDB:
    def __init__(self):
        self.rows = []

    def insert_audit(self, row):
        self.rows.append(row)
        return {"id": len(self.rows)}

    def update_case(self, session_id, changes):
        return {}


def test_stale_offer_422_becomes_a_409_retry():
    db = StandInDB()
    table = RecordingTable(StandInArena(), db, "sim")
    table.session_id, table.db_session_id = "s1", "sim-test-s1"
    events = [{"from": "sup", "status": "final_offer", "term_sheets": [{"term_sheet_id": "offer:1-4", "terms": {}}]}]
    table.threads = {"sup:1": events}
    with pytest.raises(ArenaError) as err:
        table.close("sup:1", {"action": {"type": "accept", "term_sheet_id": "offer:1-4"}})
    assert err.value.status == 409  # play() re-reads the thread and decides again
    assert db.rows and db.rows[0]["action"] == "accept"  # still logged first (write-first)
