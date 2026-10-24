"""Hollerau negotiator: dual-JSON schema, Python gates, fallback. Claude is replaced by a stand-in
client (no API key, no cost); case and thread data are the real P02 fixtures under data/."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from hollerau.negotiator import SIGNATURE, HollerauAgent, option_label

DATA = Path(__file__).resolve().parent.parent / "data"
CASES, P02_THREADS, PACKAGE = DATA / "cases" / "practice.json", DATA / "cases" / "P02_threads.json", DATA / "package"
SUP = "sup:70510"


class StandInClient:
    """Mimics anthropic.Anthropic().beta.messages.create: returns `reply` as JSON text, or raises."""

    def __init__(self, reply=None, error=None):
        self.calls = []
        self.reply, self.error = reply, error
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        block = SimpleNamespace(type="text", text=json.dumps(self.reply))
        return SimpleNamespace(stop_reason="end_turn", content=[block])


@pytest.fixture(scope="module")
def p02():
    for p in (CASES, P02_THREADS, PACKAGE):
        if not p.exists():
            pytest.skip(f"fixture missing: {p}")
    from hollerau.package import Package

    cases = {c["case_id"]: c for c in json.loads(CASES.read_text(encoding="utf-8"))}
    threads = json.loads(P02_THREADS.read_text(encoding="utf-8"))
    return cases["case:P02"], {SUP: threads[SUP][:5]}, Package(str(PACKAGE))


def _reply(action="send", price=360.0, payment="90", index="none", body="Dear Sir or Madam, please see our terms."):
    return {
        "reasoning_audit": {"observed_barrier": "Small steps only.", "strategic_intent": "Trade payment days."},
        "decision": {
            "supplier_id": SUP,
            "action": action,
            "subject": "Re: motor",
            "outbound_email_text": f"{body}\n{SIGNATURE}",
            "term_sheets": [{"unit_price": price, "payment_days": payment, "index_clause": index}],
        },
    }


def test_schema_is_strict_and_uses_option_labels(p02):
    case, threads, pkg = p02
    client = StandInClient(_reply())
    HollerauAgent(client, pkg).decide(case, threads)
    kwargs = client.calls[0]
    schema = kwargs["output_config"]["format"]["schema"]
    sheet = schema["properties"]["decision"]["properties"]["term_sheets"]["items"]
    assert sheet["additionalProperties"] is False
    assert set(sheet["required"]) == {"unit_price", "payment_days", "index_clause"}
    assert option_label(None) in sheet["properties"]["index_clause"]["enum"]
    assert kwargs["fallbacks"] == "default" and kwargs["output_config"]["effort"] in ("low", "medium", "high")
    assert kwargs["system"][1]["cache_control"] == {"type": "ephemeral"}  # the per-case brief is cached


def test_claude_send_is_mapped_priced_and_audited(p02):
    case, threads, pkg = p02
    d = HollerauAgent(StandInClient(_reply(price=360.0, payment="90")), pkg).decide(case, threads)
    msg = d["message"]
    terms = msg["term_sheets"][0]["terms"]
    assert terms["payment_days"] == 90 and terms["index_clause"] is None and terms["unit_price"] == 360.0
    audit = msg["reasoning_audit"]
    assert audit["decision_source"] == "claude" and audit["strategic_intent"] == "Trade payment days."
    assert "C_open EUR" in audit["mathematical_justification"]  # numbers written by Python
    assert audit["segment_protocol"].startswith("Strategic") and audit["c_target"] is not None


def test_sheet_worse_than_standing_is_replaced_by_target(p02):
    case, threads, pkg = p02
    d = HollerauAgent(StandInClient(_reply(price=399.0, payment="14")), pkg).decide(case, threads)
    terms = d["message"]["term_sheets"][0]["terms"]
    assert terms["unit_price"] < 399.0  # the engine's target, not Claude's worse-than-standing sheet


def test_early_accept_above_target_is_vetoed(p02):
    case, threads, pkg = p02
    d = HollerauAgent(StandInClient(_reply(action="accept")), pkg).decide(case, threads)
    assert "action" not in d["message"]  # a counter instead of accepting 370 EUR in round 3
    assert d["message"]["reasoning_audit"]["decision_source"] == "fallback"


def test_claude_outage_falls_back_to_target_counter(p02):
    import anthropic
    import httpx

    case, threads, pkg = p02
    err = anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
    d = HollerauAgent(StandInClient(error=err), pkg).decide(case, threads)
    msg = d["message"]
    assert msg["reasoning_audit"]["decision_source"] == "fallback"
    assert msg["term_sheets"] and SIGNATURE in msg["body"]


def test_dearer_option_b_is_dropped(p02):
    case, threads, pkg = p02
    reply = _reply(price=360.0, payment="90")
    reply["decision"]["term_sheets"].append({"unit_price": 366.0, "payment_days": "90", "index_clause": "none"})
    d = HollerauAgent(StandInClient(reply), pkg).decide(case, threads)
    prices = [s["terms"]["unit_price"] for s in d["message"]["term_sheets"]]
    assert prices == [360.0]  # 366 would be a concession in disguise: the supplier picks it
