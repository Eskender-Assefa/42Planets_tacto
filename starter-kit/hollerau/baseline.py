"""Record real naive-agent games into Supabase as the dashboard's layout baseline.

    cd starter-kit
    uv run python -m hollerau.baseline --sim                 # S01 + S02 on the local arena-sim
    uv run python -m hollerau.baseline --practice case:P02   # ONE hosted practice session (quota!)
    uv run python -m hollerau.baseline --purge-sim           # delete all environment='sim' rows

--sim needs `uv run arena-sim serve --no-clock --data data/package` running; it registers its own
simulator key. --practice uses ARENA_URL / ARENA_API_KEY from .env and costs 1 practice session.
"""

import argparse
import json
import logging
import os
import sys
import time
from typing import cast

import httpx

from arena_kit.agents import NaiveAgent
from arena_kit.client import ArenaClient, ArenaError
from arena_kit.play import play

from .db import DBError, SupabaseDB
from .kit import JSONObject, load_env
from .recorder import RecordingTable
from .types import Environment

log = logging.getLogger("hollerau.baseline")

SIM_URL = "http://127.0.0.1:8000"
SIM_CASES = ("case:S01", "case:S02")
TIMEOUT_S = 30.0


def run_case(client: ArenaClient, db: SupabaseDB, environment: Environment, case_id: str) -> JSONObject:
    table = RecordingTable(client, db, environment)
    result = cast(JSONObject, play(table, case_id, NaiveAgent()))  # type: ignore[no-untyped-call]
    table.finish(result)
    keep = ("deal", "supplier_id", "c_open", "c_deal", "c_best", "score")
    print(f"{case_id} -> {table.db_session_id}: " + json.dumps({k: result.get(k) for k in keep}))
    return result


def sim_client() -> ArenaClient:
    probe = ArenaClient(SIM_URL, timeout=TIMEOUT_S)  # type: ignore[no-untyped-call]
    key = probe.register(f"42Planets baseline {time.time():.0f}", "sim")["api_key"]  # type: ignore[no-untyped-call]
    return ArenaClient(SIM_URL, str(key), timeout=TIMEOUT_S)  # type: ignore[no-untyped-call]


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    load_env()
    ap = argparse.ArgumentParser(prog="hollerau.baseline", description=__doc__.split("\n\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sim", action="store_true", help=f"play {', '.join(SIM_CASES)} on the local simulator")
    mode.add_argument("--practice", metavar="CASE", help="play one hosted practice case (costs 1 session)")
    mode.add_argument("--purge-sim", action="store_true", help="delete every environment='sim' case")
    a = ap.parse_args(argv)
    try:
        db = SupabaseDB()
    except DBError as e:
        print(f"FAIL {e}")
        return 1
    try:
        if a.purge_sim:
            gone = db.delete("cases", environment="eq.sim")  # audit_logs cascade
            print(f"deleted {len(gone)} sim case(s) and their audit rows")
        elif a.sim:
            client = sim_client()
            for case_id in SIM_CASES:
                run_case(client, db, "sim", case_id)
        else:
            url = os.environ.get("ARENA_URL", "")
            if "127.0.0.1" in url or "localhost" in url:
                print("FAIL --practice needs ARENA_URL pointing at the hosted arena, not the simulator")
                return 1
            run_case(ArenaClient(), db, "practice", a.practice)  # type: ignore[no-untyped-call]
    except (DBError, ArenaError, httpx.HTTPError) as e:
        print(f"FAIL {type(e).__name__}: {e}")
        return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
