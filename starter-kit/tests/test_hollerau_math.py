"""Hollerau cost-calculation layer: envelope, telemetry, evidence, profiles.

Uses real arena data saved under data/ (gitignored, never inlined here):
  data/cases/practice.json     - `ArenaClient().cases("practice")`
  data/cases/P02_threads.json  - the recorded P02 practice session's threads
  data/package/                - `uv run arena data`
Tests skip when a fixture is missing.
"""

import json
import math
from pathlib import Path

import pytest

from hollerau.envelope import best_package, envelope, lever_table, price_for_cost, progress, safe_cost
from hollerau.kit import complete_offer, standard_terms, standing
from hollerau.profiles import config, protocol
from hollerau.telemetry import telemetry

DATA = Path(__file__).resolve().parent.parent / "data"
CASES, P02_THREADS, PACKAGE = DATA / "cases" / "practice.json", DATA / "cases" / "P02_threads.json", DATA / "package"
SUP = "sup:70510"


def _need(*paths):
    for p in paths:
        if not p.exists():
            pytest.skip(f"fixture missing: {p}")


@pytest.fixture(scope="module")
def p02():
    _need(CASES, P02_THREADS)
    cases = {c["case_id"]: c for c in json.loads(CASES.read_text(encoding="utf-8"))}
    return cases["case:P02"], json.loads(P02_THREADS.read_text(encoding="utf-8"))[SUP]


@pytest.fixture(scope="module")
def pkg():
    _need(PACKAGE)
    from hollerau.package import Package

    return Package(str(PACKAGE))


def test_config_and_protocol_fallbacks():
    cfg = config()
    assert {"leverage", "stabilise", "secure_supply"} <= set(cfg["segments"])
    p = protocol("not-a-goal", "XX")
    assert p["goal"] == "routine" and p["culture"] == cfg["cultures"]["_default"]
    assert protocol("stabilise", "DE")["segment"]["relationship"] is True


def test_price_for_cost_inverts_total_cost(p02):
    case, events = p02
    std = standard_terms(events)
    terms = complete_offer(case, standing(events)[1])
    target = safe_cost(case, terms, std) - 50_000
    price = price_for_cost(case, terms, target, std)
    assert price is not None
    assert abs(safe_cost(case, {**terms, "unit_price": price}, std) - target) < 0.01 * case["buyer"]["need_per_year"]


def test_best_package_is_cheapest_lever_combo(p02):
    case, events = p02
    std = standard_terms(events)
    base = complete_offer(case, standing(events)[1])
    terms, c = best_package(case, base, 360.0, std, None)
    assert terms["unit_price"] == 360.0
    for row in lever_table(case, {**base, "unit_price": 360.0}, std, None):
        assert c <= safe_cost(case, {**base, "unit_price": 360.0, row["field"]: row["value"]}, std) + 0.01


def test_progress_is_monotone_and_clock_aware(p02):
    case, events = p02
    turns = [progress(case, events[:k], None) for k in range(1, len(events) + 1)]
    assert turns == sorted(turns) and 0.0 <= turns[0] <= turns[-1] <= 1.0
    assert progress(case, events[:1], 90.0) == 1.0  # at the close-before-cap mark: land


def test_stabilise_target_never_below_floor_estimate(p02, pkg):
    case, events = p02
    for k in (1, 5, 9):
        env = envelope(case, {SUP: events[:k]}, [SUP], {SUP: protocol("stabilise", "DE")}, pkg, {SUP: "DE"})
        t = env["threads"][SUP]
        assert t["price_floor_est"] is not None and t["target_price"] is not None
        anchor = config()["segments"]["stabilise"]["anchor_below_target_pct"]
        assert t["target_price"] >= min(t["price_floor_est"], t["standing_price"]) * (1 - anchor / 100) - 0.01
        assert t["target_price"] <= t["standing_price"]
        assert t["c_target"] is not None and t["c_target"] <= t["c_true_standing"]
    assert env["c_open"] == pytest.approx(safe_cost(case, events[0]["term_sheets"][0]["terms"], standard_terms(events)))


def test_leverage_target_moves_toward_landing(p02):
    case, events = p02
    lev = protocol("leverage", "DE")
    early = envelope(case, {SUP: events[:1]}, [SUP], {SUP: lev}, None, {SUP: "DE"})["threads"][SUP]
    late = envelope(case, {SUP: events[:9]}, [SUP], {SUP: lev}, None, {SUP: "DE"})["threads"][SUP]
    assert early["target_price"] < late["target_price"] <= late["standing_price"]
    assert early["supplier_estimate"] is None and early["penalty_at_offer"] == 0.0


def test_telemetry_reads_the_supplier(p02):
    case, events = p02
    first = telemetry(case, SUP, events[:1], None)
    assert first["mindset"] == "opening" and first["concession_velocity"] is None
    stalled = telemetry(case, SUP, events[:7], None)
    assert stalled["concession_velocity"] is not None and stalled["concession_velocity"] >= 0
    final = telemetry(case, SUP, events[:9], None)
    assert final["mindset"] == "critical_breakoff" and final["status"] == "final_offer"
    assert final["sheet_costs"] == sorted(final["sheet_costs"], reverse=True)


def test_evidence_refs_are_citable_and_maths_is_python(pkg):
    from hollerau.evidence import build_brief

    brief = build_brief(pkg, SUP, "part:350011", 6.5)
    assert brief["index_justified_pct"] is not None and math.isfinite(brief["index_justified_pct"])
    assert brief["items"], "expected evidence for a detailed supplier"
    for item in brief["items"]:
        for ref in item["refs"]:
            assert pkg.is_citable(ref) and ref in item["sentence"]


def test_rising_index_is_never_favourable_without_an_asked_increase(pkg):
    """P08's letter names no %: a +5.9 % alloy surcharge must not be offered as our argument."""
    from hollerau.evidence import build_brief

    brief = build_brief(pkg, "sup:70710", "part:370010", None)
    for item in brief["items"]:
        if item["kind"] == "index" and "+" in item["sentence"].split("changed", 1)[1][:3]:
            assert not item["favourable"], item["sentence"]


def test_free_lever_goes_to_the_supplier_and_must_haves_hold(pkg):
    """Run 2, P11: chargeback >= our defect cost makes ppm worthless to us -> ask the loosest ppm the
    must-have allows (1500), never the strictest; never a package breaking a must-have (2500)."""
    _need(CASES, DATA / "cases" / "P11_threads.json")
    cases = {c["case_id"]: c for c in json.loads(CASES.read_text(encoding="utf-8"))}
    events = json.loads((DATA / "cases" / "P11_threads.json").read_text(encoding="utf-8"))["sup:70140"][:1]
    sup = "sup:70140"
    t = envelope(cases["case:P11"], {sup: events}, [sup], {sup: protocol("quality_first", "PL")}, pkg, {})
    target = t["threads"][sup]["target_terms"]
    assert target["ppm_commitment"] == 1500 and target["chargeback_eur_per_complaint"] == 500
