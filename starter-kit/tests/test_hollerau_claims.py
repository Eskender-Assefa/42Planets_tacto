"""Checked claims (hollerau/claims.py): the arena's citation rules (brief/api.md, "What counts"),
one claim per offer, and the term rules learned from the EHL winners (docs/winners_analysis).
Claude is a stand-in client; cases, threads and facts are the real fixtures under data/."""

import json
import re
from pathlib import Path

import pytest

from hollerau.negotiator import SIGNATURE, HollerauAgent

DATA = Path(__file__).resolve().parent.parent / "data"
CASES, PACKAGE = DATA / "cases" / "practice.json", DATA / "package"
IDX = re.compile(r"idx:([\w-]+)@(\d{4}-\d{2})")


@pytest.fixture(scope="module")
def world():
    for p in (CASES, PACKAGE):
        if not p.exists():
            pytest.skip(f"fixture missing: {p}")
    from hollerau.package import Package

    cases = {c["case_id"]: c for c in json.loads(CASES.read_text(encoding="utf-8"))}
    return cases, Package(str(PACKAGE))


def _threads(name):
    path = DATA / "cases" / f"{name}_threads.json"
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _months(m):
    return int(m[:4]) * 12 + int(m[5:7])


def _figures(sentence):
    return [float(x.replace(",", "")) for x in re.findall(r"[-+]?\d[\d,]*\.?\d*", re.sub(r"\(.*?\)", "", sentence))]


def test_every_claim_follows_the_arena_rules(world):
    """Each claim's IDs exist, its figure matches the fact within the arena's tolerance, an index
    window is two months of one of the part's cost drivers <= 12 apart ending within the last 12
    months of all index data (live post-winners check: other series and a 2025-09 end were
    'irrelevant'), and no quote of another case is cited."""
    from hollerau.claims import build_claims, data_last_month

    cases, pkg = world
    facts = pkg.data.facts
    newest = _months(data_last_month(pkg))
    seen_kinds = set()
    for case in cases.values():
        drivers = {d["series_id"] for d in pkg.cost_drivers(case["parts"][0])}
        for sup in case["suppliers"]:
            for c in build_claims(pkg, case, sup):
                seen_kinds.add(c["kind"])
                assert all(r in facts for r in c["refs"]), c
                assert not any(r.startswith(("quote:", "offer:")) for r in c["refs"]), c
                assert not re.search(r"\d,\d", c["sentence"]), c  # "2,376 ppm" was read as 2.376 (P11)
                figs = _figures(c["sentence"])
                if c["kind"] == "index":
                    (s1, m1), (s2, m2) = IDX.findall(" ".join(c["refs"]))
                    assert s1 == s2 and 1 <= _months(m2) - _months(m1) <= 12, c
                    assert s1 in drivers and newest - _months(m2) <= 11, c
                    a, b = facts[c["refs"][0]]["value"], facts[c["refs"][1]]["value"]
                    assert any(abs(f - (b / a - 1) * 100) <= 0.5 for f in figs), c
                elif c["kind"] == "notice":
                    doc, ctr = (facts[r] for r in c["refs"])
                    assert doc["days"] < ctr["days"] and {doc["days"], ctr["days"]} <= set(figs), c
                elif c["kind"] == "volume":
                    assert facts[c["refs"][0]]["change_pct"] in figs, c
                elif c["kind"] == "delivery":
                    assert facts[c["refs"][0]]["otd_pct"] in figs and "ppm" not in c["sentence"], c
                elif c["kind"] == "quality":
                    assert facts[c["refs"][0]]["ppm"] in figs, c
                elif c["kind"] == "should_cost":
                    assert facts[c["refs"][0]]["unit_cost"] in figs, c
    assert {"index", "notice", "should_cost", "volume", "delivery", "quality", "history"} <= seen_kinds


def _reply(sup, body, price, sheet_extra):
    return {
        "reasoning_audit": {"observed_barrier": "Holds its price.", "strategic_intent": "One new argument."},
        "decision": {
            "supplier_id": sup,
            "action": "send",
            "subject": "Re: offer",
            "outbound_email_text": f"{body}\n\nKind regards,\n{SIGNATURE}",
            "term_sheets": [{"unit_price": price, **sheet_extra}],
            "news_to_cite": "none",
        },
    }


class StandIn:
    def __init__(self, reply):
        from types import SimpleNamespace

        self.reply, self.calls = reply, []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        from types import SimpleNamespace

        self.calls.append(kwargs)
        usage = SimpleNamespace(
            input_tokens=0, output_tokens=0, cache_read_input_tokens=0, cache_creation_input_tokens=0
        )
        block = SimpleNamespace(type="text", text=json.dumps(self.reply))
        return SimpleNamespace(stop_reason="end_turn", content=[block], usage=usage)


def test_one_claim_per_offer_and_no_model_citations(world):
    """P02 (post-ask replay: three messages without a new argument, the supplier never moved). The
    model's own one-ID index sentence is dropped; exactly one checked claim with both IDs goes out,
    and the next offer carries the next claim, never a duplicate."""
    cases, pkg = world
    case, sup = cases["case:P02"], "sup:70510"
    events = _threads("P02")[sup][:1]
    body = "Thank you for your offer. Energy prices fell -3.7% (idx:PPI-D351@2026-08). We propose our terms."
    agent = HollerauAgent(StandIn(_reply(sup, body, 356.0, {"payment_days": "90", "index_clause": "none"})), pkg)
    d = agent.decide(case, {sup: events})
    out = d["message"]["body"]
    assert "PPI-D351" not in out  # the model's sentence is gone (and energy is no driver of this part)
    from hollerau.claims import build_claims

    expected = build_claims(pkg, case, sup)[0]
    ids = re.findall(r"\b(?:idx|sc|fc|doc|ctr|cost|po|quote|offer|news):[\w.:@#/-]*\w", out)
    assert ids == expected["refs"] and expected["sentence"] in out, out
    assert f"claim attached: {expected['kind']}" in d["message"]["reasoning_audit"]["mathematical_justification"]
    first = set(ids)
    # the supplier answers; our next offer brings a different argument
    reply = {**events[0], "message_id": "msg:70510-1-9", "from": "sales@70510", "claim_results": []}
    d2 = agent.decide(case, {sup: [*events, d["message"], reply]})
    ids2 = set(re.findall(r"\b(?:idx|sc|fc|doc|ctr|cost|po|news):[\w.:@#/-]*\w", d2["message"].get("body", "")))
    assert ids2 and not ids2 & first, d2["message"].get("body")


def test_rfq_cites_a_cheaper_rivals_live_offer_never_its_own(world):
    """Coda's RFQ pattern: quote the cheapest bidder's live offer to the dearer ones; never cite a
    supplier's own offer back to it (post-ask P07/P10/P18: 'irrelevant')."""
    cases, pkg = world
    case = cases["case:P05"]
    threads = _threads("P05")
    opening = {sid: [m for m in ev if m.get("from") != "buyer"][:1] for sid, ev in threads.items()}
    prices = {sid: ev[0]["term_sheets"][0]["terms"]["unit_price"] for sid, ev in opening.items()}
    dear = max(prices, key=prices.get)
    cheap = min(prices, key=prices.get)
    agent = HollerauAgent(StandIn(_reply(dear, "Thank you.", prices[cheap] * 0.9, {})), pkg)
    from tests.test_hollerau_negotiator import _render_args

    case_, threads_, env, tel, _ = _render_args(agent, case, opening)
    claim = agent._next_claim(dear, env)
    assert claim is not None and claim["kind"] == "rival_offer"
    assert claim["refs"] == [opening[cheap][0]["term_sheets"][0]["term_sheet_id"]]
    own = agent._next_claim(cheap, env)
    assert own is None or own["kind"] != "rival_offer"


def test_owner_run_supplier_gets_short_payment_outside_relationship_cases(world):
    """All three EHL winners offered owner-run firms 10-14 days; P01 (strategic) keeps 90 days -
    our own maths run measured that ahead (see test_strategic_terms_are_chosen_at_a_realistic_price)."""
    from hollerau.envelope import envelope, owner_run
    from hollerau.profiles import protocol

    cases, pkg = world
    case = cases["case:P05"]
    threads = _threads("P05")
    owner = next(sid for sid, ev in threads.items() if owner_run(ev))
    events = [m for m in threads[owner] if m.get("from") != "buyer"][:1]
    env = envelope(case, {owner: events}, [owner], {owner: protocol("routine", "DE")}, pkg, {owner: "DE"})
    days = sorted(o for o in case["term_options"]["payment_days"] if isinstance(o, int))
    want = next(d for d in days if d >= 14)
    assert env["threads"][owner]["target_terms"]["payment_days"] == want


def test_capacity_case_never_asks_a_shorter_lead_time(world):
    """H15: asking 28 days of a full supplier cost an overtime premium (0.55 vs 0.89); post-ask P10
    asked 54 -> 42 days and got a final offer in round 1."""
    from hollerau.envelope import envelope
    from hollerau.profiles import protocol

    cases, pkg = world
    case, sup = cases["case:P10"], "sup:70410"
    events = _threads("P10")[sup][:1]
    theirs = events[0]["term_sheets"][0]["terms"].get("lead_time_days")
    if theirs is None:
        pytest.skip("opening sheet without a lead time")
    for goal in ("routine", "leverage"):
        env = envelope(case, {sup: events}, [sup], {sup: protocol(goal, "DE")}, pkg, {sup: "DE"})
        assert env["threads"][sup]["target_terms"]["lead_time_days"] >= theirs, goal


def _p07(world, monkeypatch, claude_price):
    """P07 as recorded: Leitner 5.74 -> our 5.40 (90 d, 24 m) -> Leitner 5.61 (90 d, 24 m). The
    recorded agent then offered 5.30 - a retraction - and got a final offer."""
    from hollerau.profiles import config

    monkeypatch.setitem(config()["swaps"], "enabled", False)
    cases, pkg = world
    case, sup = cases["case:P07"], "sup:70610"
    events = _threads("P07")[sup][:3]
    reply = _reply(
        sup,
        f"We propose EUR {claude_price:.2f} per kit.",
        claude_price,
        {"payment_days": "90", "contract_months": "24"},
    )
    agent = HollerauAgent(StandIn(reply), pkg)
    return agent, case, sup, events, agent.decide(case, {sup: events})


def test_concession_path_never_retracts_and_moves_every_round(world, monkeypatch):
    """Arena rule 'no concession without a move from you': the 5.30 retraction becomes a counter
    above our previous 5.40 by at least the path's share of the C gap, below Leitner's 5.61, and
    the e-mail quotes the binding price."""
    from hollerau.envelope import safe_cost

    agent, case, sup, events, d = _p07(world, monkeypatch, 5.30)
    terms = d["message"]["term_sheets"][0]["terms"]
    assert 5.40 < terms["unit_price"] < 5.61, terms
    assert terms["payment_days"] == 90 and terms["contract_months"] == 24  # matched terms stay
    assert f"{terms['unit_price']:.2f}" in d["message"]["body"] and "5.30" not in d["message"]["body"]
    from hollerau.envelope import envelope

    te = envelope(case, {sup: events}, [sup], agent.state["protocols"], agent.pkg, agent.state["countries"])["threads"][
        sup
    ]
    floor, _ = agent._min_counter_c(case, events, te)
    assert safe_cost(case, terms, te["standard"]) >= floor - 0.5
    assert "paced to min C" in d["message"]["reasoning_audit"]["mathematical_justification"]


def test_concession_path_leaves_a_big_enough_step_alone(world, monkeypatch):
    """Claude's own step between the path's minimum and twice it goes out as written; a bigger one
    is still stopped by the concession guard."""
    agent, case, sup, events, d = _p07(world, monkeypatch, 5.48)
    assert d["message"]["term_sheets"][0]["terms"]["unit_price"] == 5.48
    audit = d["message"]["reasoning_audit"]
    assert audit["decision_source"] == "claude" and "paced" not in audit["mathematical_justification"]
    *_, d2 = _p07(world, monkeypatch, 5.58)
    assert d2["message"]["term_sheets"][0]["terms"]["unit_price"] < 5.58


def test_concession_path_holds_against_a_stonewall(world):
    """Reciprocity (live P11: Kalwisz 48.00 five times while we climbed 45.18 -> 47.18): when the
    supplier's last sheet did not get cheaper, the minimum step is our previous counter - hold."""
    from hollerau.envelope import envelope, safe_cost

    cases, pkg = world
    case, sup = cases["case:P07"], "sup:70610"
    events = _threads("P07")[sup][:3]
    stall = {**events[2], "message_id": "msg:70610-2-9", "status": "open"}  # same sheet again
    ours = {
        "from": "buyer",
        "term_sheets": [{"terms": {"unit_price": 5.45, "payment_days": 90, "contract_months": 24}}],
    }
    thread = [*events, ours, stall]
    agent = HollerauAgent(StandIn(_reply(sup, "x", 5.45, {})), pkg)
    agent.state = agent._prepare_case(case)
    te = envelope(case, {sup: thread}, [sup], agent.state["protocols"], pkg, agent.state["countries"])["threads"][sup]
    floor, prev = agent._min_counter_c(case, thread, te)
    assert abs(floor - safe_cost(case, prev, te["standard"])) < 0.01


def test_cash_short_suppliers_from_the_sunday_release_get_short_payment(world):
    """Sunday release: Vrbensky (credit cut, asks 10 days) and Pfaffenreuth (lost customer, asks 10
    days) are short of cash; Kraslin (short-time work) and Steinfelder (steel letter) are not."""
    from hollerau.envelope import distressed, owner_payment_terms

    cases, pkg = world
    if getattr(pkg.data, "release", None) is None:
        pytest.skip("Sunday release not unpacked (uv run arena data)")
    assert distressed(pkg, "sup:70170") and distressed(pkg, "sup:70190")
    assert not distressed(pkg, "sup:70270") and not distressed(pkg, "sup:70340")
    case = cases["case:P01"]  # payment_days negotiable
    days = sorted(o for o in case["term_options"]["payment_days"] if isinstance(o, int))
    terms = {"unit_price": 130.0, "payment_days": 90, "effective_date": "2027-04-01"}
    out = owner_payment_terms(case, terms, [], relationship=False, distress=True)
    assert out["payment_days"] == next(d for d in days if d >= 10)
    assert owner_payment_terms(case, terms, [], relationship=True, distress=True)["payment_days"] == 90


def test_new_supplier_from_the_final_still_gets_claims_and_a_move(world):
    """Presentation: 'The Live Final uses new suppliers that are not in practice.' A supplier our
    data does not know must cost no claim kind its records in the case file support, and the turn
    must not fall to the safety net."""
    import copy

    from hollerau.claims import build_claims

    cases, pkg = world
    new = "sup:79999"
    case = copy.deepcopy(cases["case:P11"])  # a quality case: before, an unknown supplier lost every claim
    case["suppliers"] = [new]
    case["trigger_doc"] = "doc:20261024-79999-F01"
    case["facts"] = {
        "doc:20261024-79999-F01": {"supplier": new, "days": 40, "type": "letter", "title": "Price adjustment"},
        "ctr:4600079999": {"supplier": new, "days": 90},
        "sc:79999@2026Q3": {"supplier": new, "quarter": "2026Q3", "otd_pct": 71.0, "ppm": 3100},
        "fc:310020@2026-10": {"part": "part:310020", "change_pct": 8.0, "volume_per_year": 16000},
        "news:20261024-F1": {"supplier": new, "date": "2026-10-24", "headline": "New supplier loses an order"},
    }
    kinds = {c["kind"]: c for c in build_claims(pkg, case, new)}
    assert {"quality", "notice", "volume"} <= set(kinds), kinds
    assert "3100 ppm (sc:79999@2026Q3)" in kinds["quality"]["sentence"]
    assert "40 days of notice" in kinds["notice"]["sentence"]
    events = _threads("P11")["sup:70140"][:1]
    opening = [{**m, "from": "sales@79999", "thread_id": "thread:P11:79999"} for m in events]
    agent = HollerauAgent(
        StandIn(_reply(new, "Thank you.", 43.0, {"ppm_commitment": "1500", "chargeback_eur_per_complaint": "500"})), pkg
    )
    d = agent.decide(case, {new: opening})
    audit = d["message"]["reasoning_audit"]
    assert audit["decision_source"] in ("claude", "fallback") and "Internal error" not in audit["observed_barrier"]
    assert "news:20261024-F1" in agent._news_items(new)
