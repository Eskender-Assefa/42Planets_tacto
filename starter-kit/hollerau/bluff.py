"""EXPERIMENT - competitor pressure for leverage suppliers (Desktop\\Tacto\\Bluffs.txt).

Off by default; `run.py --bluff` switches it on for one run. Leverage cases only: strategic and
bottleneck suppliers verify claims or counter-squeeze (Bluffs.txt, section 2).

A pressure ladder, decided in Python - Claude only words the claim:
  verified  a real, cheaper anchor exists: a rival's live offer in this case (RFQ) or a rival's /
            the supplier's own earlier quote - cited with its ID, so the arena can verify it
  bluff     no real anchor: "a competitive offer at around EUR X" - never an ID (a made-up ID is
            'contradicted' and costs trust), X never below floor estimate x 1.02 (Bluffs.txt:
            C_best + 2 %, with our floor estimate standing in for the hidden C_best)
After a claim: folding (velocity up) -> hold the level; called (velocity flat or a data request /
refusal in the reply) -> never repeat it, retreat to ~1 % concessions and non-price levers.
"""

from typing import Literal, TypedDict

from .envelope import Envelope, ThreadEnvelope
from .evidence import Brief
from .kit import Message
from .profiles import BluffConfig, Protocol
from .telemetry import Telemetry

Level = Literal["verified", "bluff"]
State = Literal["none", "active", "folding", "called"]


class Pressure(TypedDict):
    level: Level
    price: float  # the competitor level the claim states
    ref: str | None  # citable ID (verified only)
    ceiling: float | None  # lowest level a bluff may claim
    claim: str  # the exact sentence Claude may use (numbers from Python)


class BluffState(TypedDict):
    state: State
    level: Level | None
    price: float | None
    claimed_at: int  # our message count in the thread when the claim went out


def fresh() -> BluffState:
    return {"state": "none", "level": None, "price": None, "claimed_at": -1}


def applies(proto: Protocol) -> bool:
    return proto["goal"] == "leverage"


def verified_anchor(
    sid: str, te: ThreadEnvelope, env: Envelope, brief: Brief | None, cited: set[str], cfg: BluffConfig
) -> Pressure | None:
    """The cheapest real price below the supplier's offer: a rival's live offer or a quote."""
    price = te["standing_price"]
    if price is None:
        return None
    limit = price * (1 - cfg["verified_margin_pct"] / 100)
    candidates: list[tuple[float, str, str]] = []
    for other, ote in env["threads"].items():
        p, ref = ote["standing_price"], ote["sheet_id"]
        if other != sid and p is not None and ref and p < limit and ref not in cited:
            candidates.append((p, ref, f"We hold a competing offer at EUR {p:,.2f} per unit ({ref})."))
    for item in brief["items"] if brief else []:
        p = item.get("price")
        if item["kind"] in ("rival_quote", "own_quote") and p is not None and p < limit and item["refs"]:
            if not set(item["refs"]) & cited:
                candidates.append((p, item["refs"][0], item["sentence"]))
    if not candidates:
        return None
    p, ref, sentence = min(candidates)
    return {"level": "verified", "price": round(p, 2), "ref": ref, "ceiling": None, "claim": sentence}


def bluff_level(te: ThreadEnvelope, cfg: BluffConfig) -> Pressure | None:
    """A calibrated claim: below the offer, never below the floor estimate x (1 + margin)."""
    price, floor = te["standing_price"], te["price_floor_est"]
    if price is None:
        return None
    ceiling = floor * (1 + cfg["ceiling_over_floor_pct"] / 100) if floor else price * (1 - cfg["max_bluff_pct"] / 100)
    level = round(max(price * (1 - cfg["bluff_pct"] / 100), ceiling), 2)
    if level >= price:
        return None  # the offer is already at our ceiling: nothing credible to claim
    return {
        "level": "bluff",
        "price": level,
        "ref": None,
        "ceiling": round(ceiling, 2),
        "claim": bluff_claim(level),
    }


def bluff_claim(level: float) -> str:
    return f"We have a competitive offer at around EUR {level:,.2f} per unit."


def hold(p: Pressure, held: float | None, standing: float | None) -> Pressure:
    """Folding supplier: keep the earlier bluff level (do not escalate) while it is still below its
    offer; once the offer has passed it, the new (calibrated) level applies."""
    if p["level"] != "bluff" or held is None or standing is None or held >= standing:
        return p
    return {**p, "price": held, "claim": bluff_claim(held)}


def called_in_text(events: list[Message], cfg: BluffConfig) -> bool:
    """Did the supplier's latest reply ask for the data behind our claim or refuse to match it?"""
    last = next((m for m in reversed(events) if m.get("from") != "buyer"), None)
    body = str(last.get("body") or "").lower() if last else ""
    return any(p in body for p in cfg["called_patterns"])


def update(state: BluffState, events: list[Message], t: Telemetry, cfg: BluffConfig, stalled: float) -> BluffState:
    """After a claim went out and the supplier answered: folding, or called."""
    sent = sum(m.get("from") == "buyer" for m in events)
    if state["state"] not in ("active", "folding") or sent <= state["claimed_at"]:
        return state  # no claim pending, or no reply to it yet
    velocity = t["concession_velocity"]
    if called_in_text(events, cfg) or velocity is None or velocity < stalled:
        return {**state, "state": "called"}
    return {**state, "state": "folding"}


def used(pressure: Pressure, body: str) -> bool:
    """Did Claude actually make the claim? Verified: its ID is cited. Bluff: the claim's wording
    with its figure - a bare price could just be our own ask or a term sheet."""
    if pressure["ref"] is not None:
        return pressure["ref"] in body
    return "competitive offer" in body.lower() and f"{pressure['price']:,.2f}" in body
