"""Strong factors (Desktop\\Tacto\\strong_factors_plus.txt): volume coverage and leverage position.

Real case files and recorded practice threads under data/ (gitignored); skips without them.
"""

import json
import sys
from pathlib import Path

import pytest

from hollerau.envelope import c_alt, c_open, coverage, envelope, leverage_position, thread_envelope
from hollerau.kit import standard_terms
from hollerau.profiles import config, protocol

sys.path.insert(0, str(Path(__file__).parent))
from test_hollerau_negotiator import StandInClient, _reply  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
CASES, PACKAGE = DATA / "cases" / "practice.json", DATA / "package"


def _threads(name):
    path = DATA / "cases" / f"{name}_threads.json"
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ctx():
    for p in (CASES, PACKAGE):
        if not p.exists():
            pytest.skip(f"fixture missing: {p}")
    from hollerau.package import Package

    return {c["case_id"]: c for c in json.loads(CASES.read_text(encoding="utf-8"))}, Package(str(PACKAGE))


def test_partial_volume_offer_shows_its_uncovered_cost(ctx):
    """P10 opens with 19,890 pcs for 12 months against 23,400 pcs/year over 2 years."""
    cases, _ = ctx
    events = _threads("P10")["sup:70410"][:1]
    terms = events[0]["term_sheets"][0]["terms"]
    pct, eur = coverage(cases["case:P10"], terms, standard_terms(events))
    assert pct is not None and pct < 0.5 and eur is not None and eur > 1_000_000


def test_positions_follow_the_alternative(ctx):
    cases, _ = ctx
    expect = {"P07": "strong", "P08": "balanced", "P18": "balanced", "P11": "vulnerable", "P10": "vulnerable"}
    for name, position in expect.items():
        threads = _threads(name)
        opening = {s: [m for m in ev if m.get("from") != "buyer"][:1] for s, ev in threads.items()}
        case = cases[f"case:{name}"]
        assert leverage_position(c_open(case, opening), c_alt(case))[1] == position, name


def test_position_scaling_follows_config(ctx):
    cases, pkg = ctx
    sup, events = "sup:70710", _threads("P08")["sup:70710"][:1]
    asks = {
        pos: thread_envelope(cases["case:P08"], sup, events, protocol("leverage", "DE"), pkg, "DE", 0.0, pos)[
            "target_price"
        ]
        for pos in ("strong", "balanced", "vulnerable")
    }
    factors = config()["leverage"]["aggressiveness"]
    if factors["strong"] > factors["balanced"] > factors["vulnerable"]:
        assert asks["strong"] < asks["balanced"] < asks["vulnerable"]
    else:  # scaling switched off (all 1.0 after the factors run): position must not move the ask
        assert asks["strong"] == asks["balanced"] == asks["vulnerable"]


def test_twelve_month_counter_is_repaired_to_full_horizon(ctx):
    """P08: a 12-month counter leaves year 2 at the fallback price - full coverage is cheaper."""
    from hollerau.negotiator import HollerauAgent

    cases, pkg = ctx
    sup, events = "sup:70710", _threads("P08")["sup:70710"][:1]
    reply = _reply(price=5.40, payment="90")
    sheet = {"unit_price": 5.40, "payment_days": "90", "index_clause": "none", "contract_months": "12"}
    reply["decision"]["supplier_id"] = sup
    reply["decision"]["term_sheets"] = [sheet]
    d = HollerauAgent(StandInClient(reply), pkg).decide(cases["case:P08"], {sup: events})
    assert d["message"]["term_sheets"][0]["terms"]["contract_months"] == 24


def test_partial_sheet_is_not_accepted_early(ctx):
    from hollerau.negotiator import HollerauAgent

    cases, pkg = ctx
    sup, events = "sup:70710", _threads("P08")["sup:70710"][:1]  # 12 months = 50 % coverage
    reply = _reply(action="accept")
    reply["decision"]["supplier_id"] = sup
    reply["decision"]["term_sheets"] = []
    d = HollerauAgent(StandInClient(reply), pkg).decide(cases["case:P08"], {sup: events})
    assert "action" not in d["message"], "a partial-coverage sheet must be countered, not accepted"


def test_walk_away_only_when_every_final_offer_beats_nothing(ctx):
    from hollerau.negotiator import HollerauAgent
    from hollerau.telemetry import telemetry

    cases, pkg = ctx
    case, sup = cases["case:P08"], "sup:70710"
    events = _threads("P08")["sup:70710"]
    k = next(i for i, m in enumerate(events) if m.get("status") == "final_offer") + 1
    threads = {sup: events[:k]}
    env = envelope(case, threads, [sup], {sup: protocol("leverage", "DE")}, pkg, {sup: "DE"})
    tel = {sup: telemetry(case, sup, threads[sup], env["c_open"])}
    agent = HollerauAgent(StandInClient(), pkg)
    assert agent._rule_walk(env, tel) is None  # P08's final offer is cheaper than its alternative
    env["c_alt"] = (env["threads"][sup]["c_true_standing"] or 0) - 1  # alternative now cheaper
    assert agent._rule_walk(env, tel) == {"supplier_id": sup, "message": {"action": {"type": "walk_away"}}}
