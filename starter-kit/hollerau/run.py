"""Step 5 - the headless runner: arena_kit's play loop with our RecordingTable and agent.

    cd starter-kit
    uv run python -m hollerau.run --set sim                       # S01-S03 on the local arena-sim
    uv run python -m hollerau.run --set sim-final --waves 2       # arena-sim --final-rehearsal
    uv run python -m hollerau.run --set practice --parallel 10    # every hosted practice case (quota!)
    uv run python -m hollerau.run --set final --parallel 10       # the Live Final: start before wave 1

Options: --cases case:P02,case:P05 (subset), --agent hollerau|naive, -v (log each move).
Every move is written to Supabase before it is sent (hollerau.recorder). No browser, no prompts.
"""

import argparse
import functools
import json
import logging
import os
import sys
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import cast

import httpx

from arena_kit.agents import NaiveAgent
from arena_kit.client import ArenaClient, ArenaError
from arena_kit.play import hosted, play, quota_used_up

from .baseline import sim_client
from .db import DBError, SupabaseDB
from .kit import JSONObject, load_env
from .negotiator import new_agent_factory
from .package import Package, PackageError
from .recorder import NAIVE, RecordingTable
from .types import DecisionSource, Environment

log = logging.getLogger("hollerau.run")

type Deadline = Callable[[], float | None] | None
type AgentFactory = Callable[[Deadline], object]
CLOSING_LABEL: tuple[str, DecisionSource] = ("Kit time-cap closing move (arena_kit.play.closing_move)", "closing")


def play_one(
    client: ArenaClient,
    db: SupabaseDB,
    environment: Environment,
    case_id: str,
    new_agent: AgentFactory,
    unreasoned: tuple[str, DecisionSource],
    deadline: Deadline = None,
    wave: int | None = None,
    listing: JSONObject | None = None,
) -> JSONObject | Exception:
    table = RecordingTable(client, db, environment, wave, listing, deadline, unreasoned)
    try:
        result = cast(JSONObject, play(table, case_id, new_agent(deadline), deadline))  # type: ignore[no-untyped-call]
    except Exception as e:  # one broken case must not stop the others
        log.exception("%s failed", case_id)
        return e
    try:
        table.finish(result)
    except DBError as e:
        log.error("%s: result not stored: %s", case_id, e)
    return result


def play_set(
    client: ArenaClient,
    db: SupabaseDB,
    environment: Environment,
    case_ids: list[str],
    new_agent: AgentFactory,
    unreasoned: tuple[str, DecisionSource],
    parallel: int,
) -> dict[str, JSONObject | Exception]:
    """Practice / sim: every case at once (like arena_kit.play.play_all), stop at the quota."""
    used_up = threading.Event()

    def one(case_id: str) -> tuple[str, JSONObject | Exception]:
        if used_up.is_set():
            return case_id, ArenaError(429, "not started: the practice quota is used up")
        res = play_one(client, db, environment, case_id, new_agent, unreasoned)
        if quota_used_up(res):  # type: ignore[no-untyped-call]
            used_up.set()
            log.warning("practice quota used up: no further case starts")
        return case_id, res

    with ThreadPoolExecutor(max_workers=parallel) as pool:
        return dict(pool.map(one, case_ids))


def play_final(
    client: ArenaClient,
    db: SupabaseDB,
    environment: Environment,
    new_agent: AgentFactory,
    unreasoned: tuple[str, DecisionSource],
    waves: int,
    parallel: int,
    poll: float = 5.0,
) -> dict[str, JSONObject | Exception]:
    """The Live Final - the loop of arena_kit.play.play_waves (diff it on kit updates) with a
    RecordingTable per case and each case's wave cap passed to table and agent."""
    started: dict[str, Future[JSONObject | Exception]] = {}
    closed: set[int] = set()
    caps: dict[int, float] = {}
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        while len(closed) < waves or not all(f.done() for f in started.values()):
            try:
                cases = cast(list[JSONObject], client.cases("final"))  # type: ignore[no-untyped-call]
            except ArenaError as e:
                if e.status != 403:  # 403: no wave has started yet
                    raise
                cases = []
            for case in cases:
                wave = case.get("wave")
                if not isinstance(wave, int):
                    continue
                if not case.get("open"):
                    if wave not in closed:
                        log.warning("wave %s closed (%d of %d)", wave, len(closed) + 1, waves)
                    closed.add(wave)
                    continue
                secs = case.get("seconds_left")
                if isinstance(secs, int | float):  # each wave has its own cap; follow an extension
                    caps[wave] = time.time() + secs
                case_id = str(case.get("case_id"))
                if case_id not in started and secs:
                    if wave not in {c.get("wave") for c in cases if str(c.get("case_id")) in started}:
                        log.warning("wave %s started: %s", wave, case.get("theme"))
                    deadline = functools.partial(caps.get, wave)
                    started[case_id] = pool.submit(
                        play_one, client, db, environment, case_id, new_agent, unreasoned, deadline, wave, case
                    )
            time.sleep(poll)
    return {case_id: f.result() for case_id, f in started.items()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hollerau.run", description=__doc__.split("\n\n")[0])
    ap.add_argument("--set", required=True, choices=["sim", "sim-final", "practice", "final"])
    ap.add_argument("--cases", help="comma-separated case ids (default: every playable case of the set)")
    ap.add_argument("--agent", default="hollerau", choices=["hollerau", "naive"])
    ap.add_argument("--parallel", type=int, default=10)
    ap.add_argument("--waves", type=int, default=5)
    ap.add_argument("--bluff", action="store_true", help="EXPERIMENT: competitor pressure, leverage cases only")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if a.verbose else logging.WARNING,
        format="%(asctime)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    load_env()
    environment: Environment = "sim" if a.set.startswith("sim") else cast(Environment, a.set)
    try:
        db = SupabaseDB()
        if environment == "sim":
            client = sim_client()
        else:
            url = os.environ.get("ARENA_URL", "")
            if "127.0.0.1" in url or "localhost" in url:
                print(f"FAIL --set {a.set} needs ARENA_URL pointing at the hosted arena")
                return 1
            client = ArenaClient()  # type: ignore[no-untyped-call]
        if a.agent == "hollerau":
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("FAIL set ANTHROPIC_API_KEY in starter-kit/.env (or use --agent naive)")
                return 1
            new_agent: AgentFactory = new_agent_factory(Package(), bluff_mode=a.bluff or None)
            unreasoned = CLOSING_LABEL
        else:
            new_agent = lambda _deadline: NaiveAgent()  # type: ignore[no-untyped-call]  # noqa: E731
            unreasoned = (NAIVE, "naive")
        parallel = min(a.parallel, 10)
        if a.set in ("final", "sim-final"):
            out = play_final(client, db, environment, new_agent, unreasoned, a.waves, parallel)
        else:
            listing = cast(list[JSONObject], client.cases("practice"))  # type: ignore[no-untyped-call]
            ids = [str(c["case_id"]) for c in hosted(listing)]  # type: ignore[no-untyped-call]
            if a.cases:
                wanted = [c.strip() for c in a.cases.split(",")]
                ids = [c for c in wanted if c in ids] or wanted
            out = play_set(client, db, environment, ids, new_agent, unreasoned, parallel)
    except (DBError, PackageError, ArenaError, httpx.HTTPError) as e:
        print(f"FAIL {type(e).__name__}: {e}")
        return 1
    total = 0.0
    for case_id, res in sorted(out.items()):
        if isinstance(res, Exception):
            print(f"{case_id}: ERROR {res}")
            continue
        score = res.get("score")
        total += float(score) if isinstance(score, int | float) else 0.0
        keep = ("deal", "supplier_id", "c_open", "c_deal", "c_best", "score")
        print(f"{case_id}: " + json.dumps({k: res.get(k) for k in keep}))
    print(
        f"total score {total:.3f} over {len(out)} case(s) = {total * 10:.1f} points"
        + (" [bluff experiment ON]" if a.bluff else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
