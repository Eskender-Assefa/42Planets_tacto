"""v3 swap engine + pacing (Desktop\\Tacto\\v3_improvements.txt) on recorded practice threads."""

import json
import sys
from pathlib import Path

import pytest

from hollerau.envelope import envelope, thread_envelope
from hollerau.profiles import config, protocol
from hollerau.swaps import swaps, wants

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


def _te(ctx, name, sup, goal, k):
    cases, pkg = ctx
    case = cases["case:" + name.replace("run1", "")]
    events = _threads(name)[sup][:k]
    return case, events, envelope(case, {sup: events}, [sup], {sup: protocol(goal, "DE")}, pkg, {sup: "DE"})


def test_supplier_wants_are_read_from_its_words(ctx):
    events = _threads("P11")["sup:70140"][:3]  # "faster payment would help us more than anything"
    assert "payment_days" in wants(events, config()["swaps"])


def test_index_clause_is_sold_for_more_than_it_costs(ctx):
    """P08: Donautal demands the clause - give it only for >= premium x break-even (and >= 8 %)."""
    case, events, env = _te(ctx, "P08", "sup:70710", "leverage", 3)
    te = env["threads"]["sup:70710"]
    found = [s for s in swaps(case, te, events, config()["swaps"]) if s["field"] == "index_clause"]
    assert found
    s = found[0]
    cut_per_unit = te["standing_price"] - s["ask_price"]
    assert cut_per_unit >= s["breakeven_per_unit"] * config()["swaps"]["premium"] - 0.01
    assert s["c_true"] < te["c_true_standing"]


def test_horizon_beyond_need_is_a_free_chip(ctx):
    """P07: 36 months on a 24-month need costs us nothing - offered for a price cut."""
    case, events, env = _te(ctx, "P07", "sup:70610", "routine", 3)
    te = env["threads"]["sup:70610"]
    chip = [s for s in swaps(case, te, events, config()["swaps"]) if s["field"] == "contract_months"]
    assert chip and chip[0]["value"] == 36 and abs(chip[0]["give_cost_eur"]) <= 1.0 and chip[0]["cut_pct"] > 0


def test_stalled_supplier_gets_the_mandatory_trade_first(ctx):
    from hollerau.negotiator import HollerauAgent

    cases, pkg = ctx
    sup = "sup:70510"
    events = _threads("P02")[sup][:5]  # Nordmark stalls (0.1 % steps)
    d = HollerauAgent(StandInClient(_reply(price=364.0, payment="90")), pkg).decide(cases["case:P02"], {sup: events})
    msg = d["message"]
    assert "swap offered:" in msg["reasoning_audit"]["mathematical_justification"]
    assert msg["term_sheets"][0]["terms"]["unit_price"] < events[-1]["term_sheets"][0]["terms"]["unit_price"]


def test_pacing_holds_the_anchor_first(ctx, monkeypatch):
    """v3 hold on the old percentage curve (floor pacing off - leverage_fix replaces it there)."""
    monkeypatch.setitem(config()["floor_pacing"], "enabled", False)
    cases, pkg = ctx
    case, sup = cases["case:P08"], "sup:70710"
    events = _threads("P08")[sup][:1]
    hold = config()["pacing"]["hold_until_progress"]
    early = thread_envelope(case, sup, events, protocol("leverage", "DE"), pkg, "DE", 0.0)
    held = thread_envelope(case, sup, events, protocol("leverage", "DE"), pkg, "DE", hold * 0.9)
    later = thread_envelope(case, sup, events, protocol("leverage", "DE"), pkg, "DE", min(hold + 0.3, 1.0))
    assert early["target_price"] == held["target_price"] < later["target_price"]


def test_last_move_accepts_a_standing_sheet_that_beats_everything(ctx):
    """v3 'turn 10 hard boundary': with one message left, take a sheet below C_alt and C_open."""
    from hollerau.negotiator import HollerauAgent
    from hollerau.telemetry import telemetry

    case, events, env = _te(ctx, "P08", "sup:70710", "leverage", 5)
    sup = "sup:70710"
    tel = {sup: telemetry(case, sup, events, env["c_open"])}
    agent = HollerauAgent(StandInClient(), ctx[1])
    agent.state = agent._prepare_case(case)
    assert agent._rule_accept(case, {sup: events}, env, tel) is None  # 5 messages left: keep going
    tel[sup]["moves_left"] = 1
    rule = agent._rule_accept(case, {sup: events}, env, tel)
    assert rule is not None and rule[0]["message"]["action"]["type"] == "accept"


def test_floor_pacing_anchors_at_the_calibrated_floor_then_steps_up(ctx):
    """leverage_fix.txt: messages 1-3 at the estimated C_best, then +5 % / +15 % of the envelope."""
    from hollerau.profiles import calibration

    cases, pkg = ctx
    case, sup = cases["case:P08"], "sup:70710"
    full = _threads("P08")[sup]
    ratio = calibration()["leverage"]["floor_ratio"]
    opening = full[0]["term_sheets"][0]["terms"]["unit_price"]

    def target(k):  # our next message is number (buyer messages in events[:k]) + 1
        return thread_envelope(case, sup, full[:k], protocol("leverage", "DE"), pkg, "DE", 0.0)

    first = target(1)
    assert first["floor_ratio"] == ratio and first["price_floor_est"] == round(opening * (1 + ratio), 2)
    assert first["target_price"] == pytest.approx(first["price_floor_est"], abs=0.02)  # anchor on the floor
    fourth = target(7)  # 3 buyer messages sent -> message 4: + 5 % of the envelope
    assert first["target_price"] < fourth["target_price"] <= fourth["standing_price"]


def test_resisted_lever_gets_equal_cost_variants(ctx):
    """P11: 'a EUR 500 chargeback is too high' -> also offer lower chargebacks at prices that keep our
    C equal, so the supplier picks the relief it values most (MESO)."""
    from hollerau.envelope import safe_cost
    from hollerau.swaps import equivalents

    case, events, env = _te(ctx, "P11", "sup:70140", "quality_first", 3)
    te = env["threads"]["sup:70140"]
    variants = equivalents(case, te, events, config()["swaps"])
    assert variants
    c_target = safe_cost(case, te["target_terms"], te["standard"])
    for v in variants:
        assert v["chargeback_eur_per_complaint"] < te["target_terms"]["chargeback_eur_per_complaint"]
        assert v["unit_price"] < te["target_terms"]["unit_price"]
        assert abs(safe_cost(case, v, te["standard"]) - c_target) < 0.002 * c_target  # equivalent for us


def test_holding_counter_never_repeats_the_same_ask(ctx):
    """P05: repeating EUR 24.43 drew 'come back with a real step' - the fallback steps instead."""
    from hollerau.negotiator import HollerauAgent
    from hollerau.telemetry import telemetry

    cases, pkg = ctx
    case, sup = cases["case:P08"], "sup:70710"
    events = _threads("P08")[sup][:3]  # we already asked once; the supplier replied
    env = envelope(case, {sup: events}, [sup], {sup: protocol("leverage", "DE")}, pkg, {sup: "DE"})
    te = env["threads"][sup]
    last = HollerauAgent._last_ask(events)
    te["target_price"] = last  # make the engine target equal our last ask
    te["target_terms"] = {**te["target_terms"], "unit_price": last}
    agent = HollerauAgent(StandInClient(), pkg)
    agent.state = agent._prepare_case(case)
    tel = {sup: telemetry(case, sup, events, env["c_open"])}
    d = agent._fallback(case, {sup: events}, env, tel, sup, "test")
    new = d["message"]["term_sheets"][0]["terms"]["unit_price"]
    assert last < new < te["standing_price"]
