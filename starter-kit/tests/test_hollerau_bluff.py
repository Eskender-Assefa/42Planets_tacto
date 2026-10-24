"""EXPERIMENT: competitor pressure (hollerau/bluff.py) on recorded practice threads under data/.

Leverage only; a real anchor beats a bluff; a bluff never goes below its ceiling and never
carries an ID; the replies to run 1's unbacked claims read as 'called'; flag off = no change.
"""

import json
from pathlib import Path

import pytest

from hollerau import bluff
from hollerau.envelope import envelope
from hollerau.profiles import config, protocol
from hollerau.telemetry import telemetry

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


def _env(case, threads, pkg, goal):
    live = list(threads)
    return envelope(case, threads, live, {s: protocol(goal, "DE") for s in live}, pkg, {s: "DE" for s in live})


def test_real_quote_beats_a_bluff_for_p18(ctx):
    from hollerau.evidence import build_brief

    cases, pkg = ctx
    sup = "sup:70740"
    threads = {sup: _threads("P18")[sup][:1]}  # Rupprecht-Kessel opens at 6.10
    env = _env(cases["case:P18"], threads, pkg, "leverage")
    brief = build_brief(pkg, sup, "part:370010", None)
    p = bluff.verified_anchor(sup, env["threads"][sup], env, brief, set(), config()["bluff"])
    assert p is not None and p["level"] == "verified" and p["ref"] == "quote:7300008" and p["price"] == 5.45


def test_rfq_rival_live_offer_is_the_anchor(ctx):
    cases, pkg = ctx
    raw = _threads("P05")
    threads = {s: [m for m in ev if m.get("from") != "buyer"][:1] for s, ev in raw.items()}  # three openings
    env = _env(cases["case:P05"], threads, pkg, "leverage")
    dearest = max(env["threads"], key=lambda s: env["threads"][s]["standing_price"] or 0)
    p = bluff.verified_anchor(dearest, env["threads"][dearest], env, None, set(), config()["bluff"])
    assert p is not None and p["ref"] is not None and p["ref"].startswith("offer:")
    assert p["price"] < env["threads"][dearest]["standing_price"]


def test_bluff_never_below_its_ceiling_and_never_an_id(ctx):
    cases, pkg = ctx
    sup = "sup:70210"
    threads = {sup: _threads("P05")[sup][:1]}
    te = _env(cases["case:P05"], threads, pkg, "leverage")["threads"][sup]
    p = bluff.bluff_level(te, config()["bluff"])
    if p is None:  # offer already at the ceiling: nothing credible to claim - also correct
        return
    assert p["ref"] is None and p["ceiling"] is not None
    assert p["ceiling"] - 0.01 <= p["price"] < te["standing_price"]
    assert "(" not in p["claim"]  # no data ID in the wording


def test_run1_replies_to_unbacked_claims_read_as_called(ctx):
    cases, _ = ctx
    cfg, stalled = config()["bluff"], config()["telemetry"]["stalled_velocity_pct"]
    for name, sup in (("P08", "sup:70710"), ("P18", "sup:70740")):
        events = _threads(name)[sup][:3]  # opening, our 'second source' claim, its reply
        state: bluff.BluffState = {"state": "active", "level": "bluff", "price": 5.5, "claimed_at": 0}
        t = telemetry(cases[f"case:{name}"], sup, events, None)
        assert bluff.update(state, events, t, cfg, stalled)["state"] == "called"


def test_leverage_only_and_flag_off_changes_nothing(ctx):
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from test_hollerau_negotiator import StandInClient, _render_args

    from hollerau.negotiator import HollerauAgent

    cases, pkg = ctx
    assert not bluff.applies(protocol("stabilise", "DE")) and not bluff.applies(protocol("secure_supply", "DE"))
    sup = "sup:70740"
    threads = {sup: _threads("P18")[sup][:1]}
    off = HollerauAgent(StandInClient(), pkg, bluff_mode=False)
    assert "COMPETITOR" not in off._render(*_render_args(off, cases["case:P18"], threads))
    on = HollerauAgent(StandInClient(), pkg, bluff_mode=True)
    args = _render_args(on, cases["case:P18"], threads)
    on._prepare_pressure(threads, args[2], args[3])
    assert "COMPETITOR PRESSURE" in on._render(*args) and "quote:7300008" in on._render(*args)


def test_claim_detection_needs_the_claim_not_just_a_price():
    """Smoke run: our own ask at the same figure counted as a bluff."""
    p: bluff.Pressure = {
        "level": "bluff",
        "price": 16.42,
        "ref": None,
        "ceiling": 15.72,
        "claim": bluff.bluff_claim(16.42),
    }
    assert not bluff.used(p, "We propose EUR 16.42 per unit, payment 90 days.")
    assert bluff.used(p, "We have a competitive offer at around EUR 16.42 per unit.")
    v: bluff.Pressure = {"level": "verified", "price": 5.45, "ref": "quote:7300008", "ceiling": None, "claim": "x"}
    assert not bluff.used(v, "EUR 5.45 is our target.") and bluff.used(v, "Quoted EUR 5.45 (quote:7300008).")


def test_hold_keeps_level_and_wording_only_below_the_offer():
    p: bluff.Pressure = {
        "level": "bluff",
        "price": 15.43,
        "ref": None,
        "ceiling": 14.78,
        "claim": bluff.bluff_claim(15.43),
    }
    held = bluff.hold(p, 15.90, 16.42)
    assert held["price"] == 15.90 and "15.90" in held["claim"]
    assert bluff.hold(p, 16.50, 16.42) == p  # the offer passed the held level: the new level applies
