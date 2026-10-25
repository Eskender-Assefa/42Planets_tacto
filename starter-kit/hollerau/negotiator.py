"""Step 4 of the turn - the Hollerau negotiator: Python computes, Claude decides and writes.

Per turn (project_context.docx chronology):
  1 ingest     the thread as arena_kit.play.play() hands it over
  2 telemetry  hollerau.telemetry (velocity, mindset, claim verdicts, clock)
  3 maths      hollerau.envelope (C, true C, floor estimate, target, lever values) - no LLM
  4 decide     time-cap close / Python rule accept, else Claude -> ONE dual-JSON object
               {"reasoning_audit": {...}, "decision": {...}} (schema-enforced), then Python gates
  5 log        message["reasoning_audit"] -> hollerau.recorder writes it BEFORE the send
  6 dispatch   play() sends the message (RecordingTable strips the audit first)

Claude never computes: every figure it may use is in the prompt, and the audit's
mathematical_justification is written here from the engine's numbers.
"""

import json
import logging
import math
import os
import re
import time
from collections.abc import Callable
from typing import Literal, TypedDict, cast

import anthropic
from anthropic.types.beta import BetaMessageParam, BetaOutputConfigParam, BetaTextBlockParam

from arena_kit.agents.llm import ID_RE, LLMAgent

from . import swaps as swap_engine
from .claims import Claim, build_claims, rival_offer_claim
from .claims import favourable as claim_favourable
from .envelope import (
    Envelope,
    ThreadEnvelope,
    coverage,
    distressed,
    envelope,
    owner_run,
    price_for_cost,
    safe_cost,
    supplier_sheets,
)
from .evidence import Brief, build_brief
from .kit import (
    JSONObject,
    JSONValue,
    Message,
    Threads,
    closing_move,
    complete_offer,
    live_threads,
    must_haves_ok,
)
from .package import Package, PackageError
from .profiles import Protocol, config, protocol
from .telemetry import Telemetry, telemetry
from .types import DecisionSource

log = logging.getLogger("hollerau.negotiator")

CLOSE_BEFORE_CAP_S = 90  # arena_kit.play.CLOSE_BEFORE_CAP_S
FALLBACK_BETA = "server-side-fallback-2026-07-01"
Effort = Literal["low", "medium", "high", "xhigh", "max"]
EFFORTS: tuple[Effort, ...] = ("low", "medium", "high", "xhigh", "max")
SIGNATURE = "Hollerau Pumpenwerke Procurement"
# evidence judged against the live offer: favourable when the cited price is below offer x factor
PRICE_EVIDENCE = {"should_cost": 0.97, "own_quote": 0.995, "rival_quote": 0.995}

SYSTEM = f"""You are the lead buyer of Hollerau Pumpenwerke GmbH, a German pump maker, negotiating by
e-mail with industrial suppliers in the Tacto Negotiation Arena. Each turn you get the case, the
financial envelope computed by our cost engine, supplier telemetry, data-backed evidence and the
thread. You choose the next move and write the e-mail.

Scoring: the arena prices every deal with a published cost function C (price, payment terms,
freight, index clause, uncovered need and - in strategic and bottleneck cases - a charge for leaving
the supplier below a sustainable margin). Lower C is better. A deal costing more than C_open scores
nothing; no deal scores nothing unless the alternative is cheaper.

Rules:
1. Numbers come from the engine, never from you. Do not calculate. Use only prices, euro figures and
   percentages shown in ENVELOPE, LEVERS or EVIDENCE, copied exactly.
2. Term sheets bind; the e-mail explains them. Mention a price in the e-mail only if it is in one of
   your term sheets.
3. Propose 1-3 term sheets. Several sheets must be equally good for us (about the same C,
   different shape, e.g. lower price with shorter payment vs. higher price with longer payment) -
   the supplier picks the one it likes, so never add a dearer fallback option. Ask near the
   TARGET; never ask a price above the supplier's standing
   price; in strategic and bottleneck cases never go below the supplier's estimated floor (it costs
   us and they may walk).
4. Trade, don't only haggle: offer levers that are cheap for us (negative or small EUR in LEVERS) in
   return for price; avoid levers that are expensive for us unless the price drop more than pays for
   them.
5. Evidence: when a supplier block shows EVIDENCE THIS TURN, Python adds that one checked sentence to
   your e-mail - never write data IDs (idx:, sc:, fc:, doc:, quote:, offer: ...) or copy EVIDENCE
   figures yourself; you may refer to the point in words ("as the index data shows"). One new
   argument per e-mail moves suppliers most. Optionally pick one news item (news_to_cite) instead,
   only if it clearly weakens the supplier's position (spare capacity, lost customer, falling
   costs); else "none". Without EVIDENCE THIS TURN: cite at most 3 data IDs, each with its figure in
   the same sentence, copied from EVIDENCE; never an ID under ALREADY CITED or a context-only item.
6. Read the supplier: stalled -> change the package, not just the price; final_offer or critical ->
   one last small push at most, then close; yielding -> keep your concessions small.
7. accept takes the supplier's standing sheet as it is; walk_away ends the case without a deal (only
   when the alternative is clearly cheaper than every offer).
8. Never reveal urgency, our budget, our targets, our alternative's price, our cost model's internals
   or that an alternative is missing (citing a quote ID listed in EVIDENCE is fine). Stay polite
   and factual; follow the CULTURE protocol. E-mail at most 120 words, plain text, signed
   "{SIGNATURE}", no placeholders.
9. No bluffing: never claim a second source, competing offer, cost trend or volume without a data
   ID from EVIDENCE backing it - suppliers answer unbacked claims with "send us the data" and do not
   move. If the supplier asks for data, cite an ID or drop the point.
10. Linked demands: when the supplier ties a demand to a lever you offered (e.g. an index clause
   for a longer contract), compare PACKAGES and withdraw the lever if the demand costs more than it
   saves.
11. Answer the supplier's questions when the answer is cheap for us (e.g. a binding volume up to our
   yearly need costs nothing) - it buys price.
12. Coverage: when an offer covers less than 100% of our need over the horizon (COVERAGE line),
   demand guaranteed pricing for the full volume over the full contract period - the uncovered
   rest is bought at the expensive fallback price.
13. Trades: never give a lever the supplier wants (payment days, index clause, longer contract,
   volume, freight) without the matching price cut listed in SWAPS - those cuts are computed by our
   cost engine. When SWAPS marks a trade as MANDATORY, your first term sheet must be exactly it.
14. Ask, never only ask: in your first e-mail to each supplier (and when it stalls), after your
   offer, ask which non-price terms - payment days, volume commitment, contract length, index clause,
   lead time - would let it improve its price most, and invite its best alternative packages.
15. Owner-run suppliers (marked OWNER-RUN) value fast payment more than anything: keep the TARGET's
   short payment term in your sheets. Capacity cases: never ask a shorter lead time than the
   supplier offers - it is the term it cannot give.
16. reasoning_audit: observed_barrier = the resistance or signal you see from the supplier;
   strategic_intent = why this move and package, in one or two sentences, without numbers you did
   not copy."""


RULE_6_MINDSET = """6. Read the supplier: stalled -> change the package, not just the price; final_offer or critical ->
   one last small push at most, then close; yielding -> keep your concessions small."""
RULE_6_PLAIN = """6. Judge each supplier move on its terms and the engine's numbers; a final_offer is the supplier's
   stated last word - accept it, or push on only when the gap to TARGET is worth the risk of a walk."""


def system_prompt() -> str:
    """SYSTEM, with rule 6 free of the inferred supplier mindset while that is quarantined."""
    return SYSTEM if config()["mindset_inference"]["enabled"] else SYSTEM.replace(RULE_6_MINDSET, RULE_6_PLAIN)


class CaseState(TypedDict):
    case_id: str
    protocols: dict[str, Protocol]
    countries: dict[str, str | None]
    briefs: dict[str, Brief]
    claims: dict[str, list[Claim]]  # per supplier: the checked-claim queue, strongest first
    labels: dict[str, dict[str, JSONValue]]  # field -> option label -> option value


def option_label(value: JSONValue) -> str:
    if value is None:
        return "none"
    if isinstance(value, dict):
        share, band = value.get("material_share"), value.get("deadband_pct")
        share_s = f"{share:.0%}" if isinstance(share, int | float) else "?"
        return f"{value.get('series')} index clause, {share_s} material share, {band}% deadband"
    return str(value)


def _eur(v: float | None) -> str:
    return "n/a" if v is None else f"EUR {v:,.2f}"


def _num(v: JSONValue) -> float | None:
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) else None


class HollerauAgent(LLMAgent):  # upstream LLMAgent is unannotated: super() calls are marked
    def __init__(
        self,
        client: anthropic.Anthropic,
        pkg: Package | None,
        model: str | None = None,
        effort: str | None = None,
        deadline: Callable[[], float | None] | None = None,
    ) -> None:
        super().__init__(None, pkg.data if pkg else None)  # type: ignore[no-untyped-call]
        self.client, self.pkg, self.deadline = client, pkg, deadline
        self.model = model or os.environ.get("LLM_MODEL") or "claude-opus-5-5"
        e = effort or os.environ.get("LLM_EFFORT") or "low"
        self.effort: Effort = next((x for x in EFFORTS if x == e), "low")
        self.state: CaseState | None = None
        self.case_brief = ""
        self.cited: set[str] = set()
        self.cited_offers: set[tuple[str, str]] = set()  # (supplier, rival offer id): once per supplier
        self.c_open: float | None = None
        self.seen: dict[str, float] = {}  # supplier message_id -> when this agent first saw it
        self.shown_attachments: set[str] = set()
        self.alt_proposed: set[tuple[str, str]] = set()  # (supplier, alternative terms) already proposed back
        self.asked: dict[str, int] = {}  # supplier -> our message number when we last asked for options
        self.swaps: dict[str, list[swap_engine.Swap]] = {}
        self.mandatory: dict[str, swap_engine.Swap] = {}

    # -- per case ------------------------------------------------------------------------------

    def _prepare_case(self, case: JSONObject) -> CaseState:
        """Before the clock matters: protocols, evidence and the cached case brief."""
        suppliers = [str(s) for s in case.get("suppliers") or []]  # type: ignore[union-attr]
        parts = case.get("parts")
        part = str(parts[0]) if isinstance(parts, list) and len(parts) == 1 else None
        buyer = case.get("buyer")
        goal = buyer.get("category_goal") if isinstance(buyer, dict) else None
        countries: dict[str, str | None] = {}
        asked: dict[str, float | None] = {}
        trigger = case.get("trigger_doc")
        for sid in suppliers:
            try:
                countries[sid] = self.pkg.supplier(sid)["country"] if self.pkg else None
            except PackageError:
                countries[sid] = None
        if self.pkg and isinstance(trigger, str):
            try:
                doc = self.pkg.trigger_document(trigger)
                if doc["supplier_id"]:
                    asked[doc["supplier_id"]] = doc["asked_pct"]
            except PackageError as e:
                log.warning("trigger document %s: %s", trigger, e)
        opts = case.get("term_options")
        labels: dict[str, dict[str, JSONValue]] = {}
        if isinstance(opts, dict):
            for field, values in opts.items():
                if isinstance(values, list):
                    labels[field] = {option_label(v): v for v in values}
        state: CaseState = {
            "case_id": str(case.get("case_id")),
            "protocols": {sid: protocol(goal if isinstance(goal, str) else None, countries[sid]) for sid in suppliers},
            "countries": countries,
            "briefs": {sid: build_brief(self.pkg, sid, part, asked.get(sid)) for sid in suppliers} if self.pkg else {},
            "claims": {sid: build_claims(self.pkg, case, sid) for sid in suppliers},
            "labels": labels,
        }
        facts = case.get("facts")
        for ref, fact in facts.items() if isinstance(facts, dict) else []:
            # the final's new suppliers: news that exists only in the case file joins the candidates
            if ref.startswith("news:") and isinstance(fact, dict) and fact.get("supplier") in state["briefs"]:
                brief = state["briefs"][str(fact["supplier"])]
                if not any(ref in i["refs"] for i in brief["items"]):
                    sentence = f"{fact.get('date', '')}: {fact.get('headline', '')} ({ref})."
                    brief["items"].append({"kind": "news", "sentence": sentence, "refs": [ref], "favourable": False})
        self.case_brief = str(super().prepare(case))  # type: ignore[no-untyped-call]
        self.cited = set()
        self.cited_offers = set()
        self.c_open = None
        self.seen = {}
        self.shown_attachments = set()
        self.alt_proposed = set()
        self.asked = {}
        self.swaps, self.mandatory = {}, {}
        return state

    def _seconds_left(self) -> float | None:
        cap = self.deadline() if self.deadline else None
        return max(0.0, cap - time.time()) if cap else None

    # -- the turn ------------------------------------------------------------------------------

    def decide(self, case: JSONObject, threads: Threads) -> JSONObject:
        try:
            return self._decide(case, threads)
        except Exception:  # a bug in our layer must not lose the case
            secs = self._seconds_left()
            if secs is not None and secs < CLOSE_BEFORE_CAP_S:
                log.exception("negotiator failed at the cap - kit closing move")
                return closing_move(case, threads)
            log.exception("negotiator failed - naive counter as safety net")
            d = cast(JSONObject, self.fallback.decide(case, threads))  # type: ignore[no-untyped-call]
            msg = d.get("message")
            if isinstance(msg, dict):
                msg["reasoning_audit"] = {
                    "observed_barrier": "Internal error in the Hollerau layer (see runner log).",
                    "strategic_intent": "Safety net: the kit's naive move keeps the case alive.",
                    "mathematical_justification": "-",
                    "decision_source": "fallback",
                }
            return d

    def _decide(self, case: JSONObject, threads: Threads) -> JSONObject:
        if self.state is None or self.state["case_id"] != case.get("case_id"):
            self.state = self._prepare_case(case)
        state = self.state
        secs = self._seconds_left()
        live = live_threads(threads)
        for sid in live:  # a supplier the case file did not list (e.g. an RFQ newcomer)
            if sid not in state["protocols"]:
                state["protocols"][sid] = protocol(None, None)
                state["countries"][sid] = None
        env = envelope(case, threads, live, state["protocols"], self.pkg, state["countries"], secs)
        # C_open is the score's zero line: freeze the first value (later quote PDFs change the
        # standard terms the opening sheet would be priced with)
        if self.c_open is None:
            self.c_open = env["c_open"]
        env["c_open"] = self.c_open
        tel = {sid: telemetry(case, sid, threads[sid], env["c_open"]) for sid in live}

        if secs is not None and secs < CLOSE_BEFORE_CAP_S:
            d = self._close(case, threads, env)
            return self._with_audit(case, d, env, tel, "closing", "Wave cap near.", "Close on the best sheet.")

        walk = self._rule_walk(env, tel)
        if walk is not None:
            return self._with_audit(
                case,
                walk,
                env,
                tel,
                "rule",
                "Best final offer costs more than our alternative.",
                "Walk away deliberately: the alternative scores better than this deal.",
            )
        rule = self._rule_accept(case, threads, env, tel)
        if rule is not None:
            decision, (observed, intent) = rule
            return self._with_audit(case, decision, env, tel, "rule", observed, intent)

        # 60 s rule per thread: three late replies end it (P05: two RFQ suppliers lost to neglect).
        # A thread waiting too long gets a fast Python holding counter - unless it is our best
        # supplier, then Claude is asked about that thread only.
        neglected = self._neglected_thread(threads, live)
        if neglected is not None and neglected != env["best_supplier"] and len(live) > 1:
            held = self._fallback(case, threads, env, tel, neglected, "Thread close to the 60 s limit.")
            self._pace(case, held, env, threads)
            self._attach_claim(held, env)
            self._remember_citations(held)
            return held
        focus = [neglected] if neglected is not None else None
        self._prepare_swaps(case, threads, env, tel)

        news_id: str | None = None
        try:
            raw, latency = self._ask_claude(case, threads, env, tel, secs, focus)
            dec = raw.get("decision")
            pick = dec.get("news_to_cite") if isinstance(dec, dict) else None
            news_id = pick if isinstance(pick, str) and pick != "none" else None
            checked = self._validate(case, threads, env, tel, raw, latency)
        except (anthropic.APIError, ValueError, KeyError, TypeError, StopIteration) as e:
            log.warning("Claude unavailable or invalid (%s) - deterministic move", e)
            checked = None
        if checked is None:
            checked, news_id = self._fallback(case, threads, env, tel), None
        self._note_swap(checked)
        self._pace(case, checked, env, threads)
        self._attach_claim(checked, env, news_id)
        self._ask_for_options(checked, threads, tel)
        self._remember_citations(checked)
        return checked

    def _take_alternative(
        self, case: JSONObject, sid: str, te: ThreadEnvelope, status: str | None, moves_left: int
    ) -> tuple[JSONObject, tuple[str, str]] | None:
        """Only the main sheet of a supplier message can be accepted, but its alternatives say what
        it will also sign - and price the terms it charges for (P10: 12 days less lead time cost
        EUR 1.90/unit). When an alternative is clearly cheaper for us, propose exactly it back
        instead of accepting the main sheet: no push on price, the supplier wrote those terms.
        Once per alternative; needs a message to spare for the supplier's 'agreed'."""
        if status == "agreed" or moves_left < 2 or te["c_true_standing"] is None:
            return None
        cfg = config()["alternatives"]
        main_c = te["c_true_standing"]
        best = None
        for o in te["offers"][1:]:  # [0] is the main sheet
            c = o["c_true"]
            key = (sid, json.dumps(o["terms"], sort_keys=True))
            if c is None or key in self.alt_proposed or not must_haves_ok(case, o["terms"], te["standard"]):
                continue
            if main_c - c >= max(cfg["min_gain_eur"], main_c * cfg["min_gain_pct"] / 100) and (
                best is None or c < best[0]
            ):
                best = (c, o["terms"], key)
        if best is None:
            return None
        c, terms, key = best
        self.alt_proposed.add(key)
        # exactly the supplier's terms (complete_offer would snap e.g. a 54-day lead time to an option)
        neg = case.get("negotiable")
        sheet: JSONObject = {k: v for k, v in terms.items() if isinstance(neg, list) and k in neg} or dict(terms)
        price = sheet.get("unit_price")
        body = (
            "Dear Sir or Madam,\n\nthank you for your offer. We would like to go ahead on your alternative terms"
            + (f" at a unit price of EUR {price:,.2f}" if isinstance(price, int | float) else "")
            + " as attached. Please confirm so we can conclude.\n\nKind regards,\n"
            + SIGNATURE
        )
        d: JSONObject = {
            "supplier_id": sid,
            "message": {"subject": f"Re: {case.get('title')}", "body": body, "term_sheets": [{"terms": sheet}]},
        }
        why = f"Its alternative costs us {_eur(main_c - c)} less than its main sheet."
        return d, (why, "Take the supplier's own cheaper alternative instead of its main sheet.")

    def _ask_for_options(self, d: JSONObject, threads: Threads, tel: dict[str, Telemetry]) -> None:
        """Ask the supplier what beyond price would let it improve - attached to an offer, never a
        message of its own (every message costs a round). Answers feed the alternative and swap
        engines: P10/P18's best scores came from supplier alternatives taken back."""
        cfg = config()["ask_options"]
        sid = str(d.get("supplier_id"))
        msg = d.get("message")
        if not cfg["enabled"] or not isinstance(msg, dict) or msg.get("action") or not msg.get("term_sheets"):
            return
        body = msg.get("body")
        if not isinstance(body, str):
            return
        sent = sum(m.get("from") == "buyer" for m in threads.get(sid, []))
        t = tel.get(sid)
        stalled = t is not None and t["mindset"] == "stalled"
        last = self.asked.get(sid)
        due = last is None or (stalled and sent - last >= cfg["repeat_after_messages"])
        if not due or (t is not None and t["moves_left"] <= 2):
            return
        self.asked[sid] = sent
        if any(marker in body.lower() for marker in cfg["markers"]):
            return  # Claude already asked in its own words
        msg["body"] = self._insert_before_closing(body, cfg["question"])

    # -- concession path: move every round, never back (config concession_path) ------------------

    @staticmethod
    def _previous_counter(events: list[Message]) -> JSONObject | None:
        """Terms of our last counter-sheet in this thread (the first sheet of our last offer)."""
        for m in reversed(events):
            sheets = m.get("term_sheets")
            if m.get("from") == "buyer" and isinstance(sheets, list) and sheets:
                first = sheets[0]
                terms = first.get("terms") if isinstance(first, dict) else None
                if isinstance(terms, dict):
                    return terms
        return None

    def _min_counter_c(
        self, case: JSONObject, events: list[Message], te: ThreadEnvelope
    ) -> tuple[float, JSONObject] | None:
        """(the least C our next counter may cost us, our previous counter's terms): our previous C
        plus a shrinking share of the gap to the supplier's standing sheet - in C, so any package
        shape compares. None before our first counter or without a gap."""
        cfg = config()["concession_path"]
        prev = self._previous_counter(events)
        standing = te["c_standing"]
        if not cfg["enabled"] or prev is None or standing is None:
            return None
        c_prev = safe_cost(case, prev, te["standard"])
        if not math.isfinite(c_prev):
            return None
        n = sum(m.get("from") == "buyer" for m in events) + 1
        share = next((s for lim, s in cfg["shares"] if n <= lim), cfg["shares"][-1][1])
        # reciprocity: a supplier that did not move gets no move from us - hold, never retract
        # (live P11: Kalwisz sat at 48.00 for five rounds while the path walked us 45.18 -> 47.18)
        theirs = [safe_cost(case, t, te["standard"]) for _, t in supplier_sheets(events)]
        if len(theirs) >= 2 and theirs[-1] > theirs[-2] - cfg["moved_min_pct"] / 100 * abs(theirs[-2]):
            share = 0.0
        return c_prev + max(standing - c_prev, 0.0) * share, prev

    def _pace(self, case: JSONObject, d: JSONObject, env: Envelope, threads: Threads) -> None:
        """Arena rule: 'no concession without a move from you'. Every counter concedes at least the
        path's share (raise its price just enough), never asks more than our previous counter, and
        keeps a term we already matched with the supplier (P18: 5.06 -> 4.88 and a deadband taken
        back -> it walked). Only ever raises our price, never above the supplier's own sheet."""
        sid = str(d.get("supplier_id"))
        msg = d.get("message")
        te = env["threads"].get(sid)
        if te is None or not isinstance(msg, dict) or msg.get("action") or not msg.get("term_sheets"):
            return
        events = threads.get(sid, [])
        got = self._min_counter_c(case, events, te)
        if got is None or te["c_standing"] is None:
            return
        floor, prev = got
        cap = te["c_standing"] - 0.01  # a sheet as dear as theirs is no counter
        std, standing = te["standard"], te["standing_terms"]
        neg = case.get("negotiable")
        fields = [str(f) for f in neg if f != "unit_price"] if isinstance(neg, list) else []
        changed: list[tuple[float, float]] = []
        for s in msg["term_sheets"]:  # type: ignore[union-attr]
            terms = s.get("terms") if isinstance(s, dict) else None
            if not isinstance(terms, dict):
                continue
            for f in fields:  # a term we already matched with the supplier stays matched
                if f in prev and prev.get(f) == standing.get(f) and terms.get(f) != prev.get(f):
                    terms[f] = prev[f]
            old = _num(terms.get("unit_price"))
            if old is None or safe_cost(case, terms, std) >= floor:
                continue
            need = min(floor, cap)
            new = price_for_cost(case, terms, need, std)
            if new is not None and safe_cost(case, {**terms, "unit_price": new}, std) < need:
                new = round(new + 0.01, 2)  # the search rounds to the nearest cent: round up instead
            if new is not None and new > old:
                terms["unit_price"] = new
                changed.append((old, new))
        if not changed:
            return
        body = msg.get("body")
        if isinstance(body, str):
            for old, new in changed:  # keep the e-mail's figures equal to the binding sheets
                body = body.replace(f"{old:,.2f}", f"{new:,.2f}").replace(f"{old:.2f}", f"{new:.2f}")
            msg["body"] = body
        audit = msg.get("reasoning_audit")
        if isinstance(audit, dict) and isinstance(audit.get("mathematical_justification"), str):
            moves = ", ".join(f"{a:.2f}->{b:.2f}" for a, b in changed)
            audit["mathematical_justification"] = (
                str(audit["mathematical_justification"]) + f" | paced to min C {_eur(floor)}: {moves}"
            )

    # -- checked claims, one per offer (claims.py) ------------------------------------------------

    def _news_items(self, sid: str) -> dict[str, str]:
        """Citable news / release items about this supplier not cited yet: id -> sentence."""
        brief = self.state["briefs"].get(sid) if self.state else None
        items = brief["items"] if brief else []
        return {
            i["refs"][0]: i["sentence"]
            for i in items
            if i["kind"] in ("news", "release") and len(i["refs"]) == 1 and i["refs"][0] not in self.cited
        }

    def _next_claim(self, sid: str, env: Envelope) -> Claim | None:
        """This turn's claim for `sid`: in an RFQ a cheaper rival's live offer first, then the case's
        queue in order - skipping IDs already cited (duplicates) and EUR figures above the offer."""
        if self.state is None or sid not in env["threads"]:
            return None
        te = env["threads"][sid]
        price = te["standing_price"]
        cfg = config()["claims"]
        rivals: list[tuple[float, str]] = []
        for other, x in env["threads"].items():
            if other != sid and x["sheet_id"] and x["standing_price"] is not None:
                rivals.append((x["standing_price"], x["sheet_id"]))
        if rivals and price is not None:
            low, offer_id = min(rivals)
            if low < price * cfg["rival_offer_factor"] and (sid, offer_id) not in self.cited_offers:
                return rival_offer_claim(offer_id, low)
        for claim in self.state["claims"].get(sid, []):
            if any(r in self.cited for r in claim["refs"]):
                continue
            factor = PRICE_EVIDENCE.get(claim["kind"], PRICE_EVIDENCE["own_quote"])
            if claim_favourable(claim, price, factor):
                return claim
        return None

    @staticmethod
    def _strip_ids(body: str) -> str:
        """Drop every sentence that cites a data ID: the model's own citations were the ones the arena
        found irrelevant or could not read (a window needs both idx IDs)."""
        out = []
        for line in body.split("\n"):
            if ID_RE.search(line):
                kept = [s for s in re.split(r"(?<=[.!?])\s+", line) if not ID_RE.search(s)]
                line = " ".join(kept)
                if not line.strip():
                    continue
            out.append(line)
        return "\n".join(out)

    def _attach_claim(self, d: JSONObject, env: Envelope, news_id: str | None = None) -> None:
        """Exactly one new checked claim on every offer we send (docs/winners_analysis)."""
        if not config()["claims"]["enabled"]:
            return
        sid = str(d.get("supplier_id"))
        msg = d.get("message")
        if not isinstance(msg, dict) or msg.get("action") or not msg.get("term_sheets"):
            return
        body = msg.get("body")
        if not isinstance(body, str):
            return
        body = self._strip_ids(body)
        news = self._news_items(sid)
        claim: Claim | None = None
        if news_id and news_id in news:
            claim = {"kind": "news", "sentence": news[news_id], "refs": [news_id], "price": None}
        else:
            claim = self._next_claim(sid, env)
        if claim is not None:
            body = self._insert_before_closing(body, claim["sentence"])
            if claim["kind"] == "rival_offer":
                self.cited_offers.add((sid, claim["refs"][0]))
            audit = msg.get("reasoning_audit")
            if isinstance(audit, dict) and isinstance(audit.get("mathematical_justification"), str):
                audit["mathematical_justification"] = (
                    str(audit["mathematical_justification"]) + f" | claim attached: {claim['kind']}"
                )
        msg["body"] = body

    @staticmethod
    def _insert_before_closing(body: str, text: str) -> str:
        """Put `text` before the e-mail's closing (greeting line and/or our signature)."""
        lines = body.split("\n")
        closings = ("kind regards", "best regards", "regards", "sincerely", "mit freundlichen", "yours")
        at = next((i for i, line in enumerate(lines) if SIGNATURE in line), len(lines))
        if at > 0 and lines[at - 1].strip().lower().startswith(closings):
            at -= 1
        while at > 0 and not lines[at - 1].strip():
            at -= 1
        rest = lines[at:]
        while rest and not rest[0].strip():
            rest.pop(0)
        return "\n".join([*lines[:at], "", text, "", *rest]).strip()

    def _neglected_thread(self, threads: Threads, live: list[str]) -> str | None:
        """The live thread whose unanswered supplier message has waited longest, if longer than
        the keep-alive limit. Arrival times are when this agent first saw each message."""
        now = time.monotonic()
        oldest: tuple[float, str] | None = None
        for sid in live:
            events = threads.get(sid, [])
            for m in events:
                mid = m.get("message_id")
                if m.get("from") != "buyer" and isinstance(mid, str):
                    self.seen.setdefault(mid, now)
            last = events[-1] if events else None
            mid = last.get("message_id") if last else None
            if last is None or last.get("from") == "buyer" or not isinstance(mid, str):
                continue
            age = now - self.seen[mid]
            if oldest is None or age > oldest[0]:
                oldest = (age, sid)
        limit = config()["llm"]["keepalive_s"]
        return oldest[1] if oldest and oldest[0] > limit else None

    def _rule_accept(
        self, case: JSONObject, threads: Threads, env: Envelope, tel: dict[str, Telemetry]
    ) -> tuple[JSONObject, tuple[str, str]] | None:
        """Python accepts outright when
        - a standing sheet already meets our target,
        - the supplier agreed to our own sheet, or
        - the supplier made its final_offer (pushing after that makes it walk - P05/P10 in the
          first practice run) and that offer is the cheapest live one.
        Always only if it beats the alternative and C_open and keeps the must-haves."""
        alt, c_open = env["c_alt"], env["c_open"]
        priced = [x["c_true_standing"] for x in env["threads"].values() if x["c_true_standing"] is not None]
        cheapest_live = min(priced) if priced else None
        switch = config()["rule_accept"]  # quarantine: a silenced trigger leaves the move to Claude
        for sid, te in env["threads"].items():
            status = tel[sid]["status"]
            sheet_id, terms, c = te["sheet_id"], te["standing_terms"], te["c_true_standing"]
            if sheet_id is None or c is None:
                continue
            last_move = tel[sid]["moves_left"] <= 1  # the hard boundary is a safety close: never silenced
            silenced = {
                "agreed": not switch["on_agreed"],
                "final_offer": not switch["on_final_offer"],
            }.get(status or "", not switch["on_target"])
            if silenced and not last_move:
                continue
            target = te["c_target"]
            if status == "final_offer":
                if cheapest_live is not None and c > cheapest_live + 0.01:
                    continue  # another supplier is cheaper: keep negotiating there
            elif status != "agreed" and tel[sid]["moves_left"] > 1 and (target is None or c > target):
                continue
            elif self._partial_negotiable(case, te) and tel[sid]["moves_left"] > 1:
                continue  # demand full coverage first (strong_factors_plus.txt: reject partial offers)
            if (alt is not None and c >= alt) or (c_open is not None and c >= c_open):
                continue
            if not must_haves_ok(case, terms, te["standard"]):
                continue
            proposal = self._take_alternative(case, sid, te, status, tel[sid]["moves_left"])
            if proposal is not None:
                return proposal
            d: JSONObject = {
                "supplier_id": sid,
                "message": {"action": {"type": "accept", "term_sheet_id": sheet_id}},
            }
            why = {
                "agreed": "Supplier agreed to our sheet.",
                "final_offer": "Supplier declared its final offer.",
            }.get(status or "", "Standing sheet already at or below our target.")
            return d, (why, "Accept: further pushing risks the walk-away.")
        return None

    # -- Claude --------------------------------------------------------------------------------

    def _schema(self, case: JSONObject, live: list[str]) -> JSONObject:
        assert self.state is not None
        neg = case.get("negotiable")
        sheet: JSONObject = {"unit_price": {"type": "number"}}
        for f in [str(x) for x in neg] if isinstance(neg, list) else []:
            if f == "unit_price":
                continue
            labels = self.state["labels"].get(f)
            sheet[f] = {"type": "string", "enum": list(labels)} if labels else {"type": "number"}
        decision: JSONObject = {
            "supplier_id": {"type": "string", "enum": cast(JSONValue, live)},
            "action": {"type": "string", "enum": ["send", "accept", "walk_away"]},
            "subject": {"type": "string"},
            "outbound_email_text": {"type": "string"},
            "term_sheets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": sheet,
                    "required": list(sheet),
                    "additionalProperties": False,
                },
            },
        }
        if config()["claims"]["enabled"]:
            news = sorted({i for sid in live for i in self._news_items(sid)})
            decision["news_to_cite"] = {"type": "string", "enum": cast(JSONValue, ["none", *news])}
        return {
            "type": "object",
            "properties": {
                "reasoning_audit": {
                    "type": "object",
                    "properties": {"observed_barrier": {"type": "string"}, "strategic_intent": {"type": "string"}},
                    "required": ["observed_barrier", "strategic_intent"],
                    "additionalProperties": False,
                },
                "decision": {
                    "type": "object",
                    "properties": decision,
                    "required": list(decision),
                    "additionalProperties": False,
                },
            },
            "required": ["reasoning_audit", "decision"],
            "additionalProperties": False,
        }

    def _ask_claude(
        self,
        case: JSONObject,
        threads: Threads,
        env: Envelope,
        tel: dict[str, Telemetry],
        secs: float | None,
        focus: list[str] | None = None,
    ) -> tuple[JSONObject, int]:
        cfg = config()["llm"]
        t0 = time.monotonic()
        system: list[BetaTextBlockParam] = [
            {"type": "text", "text": system_prompt()},
            {"type": "text", "text": self.case_brief, "cache_control": {"type": "ephemeral"}},  # per case
        ]
        prompt = self._render(case, threads, env, tel, secs)
        if focus:
            prompt += f"\nThis turn you must write to {focus[0]}: its reply is close to the 60-second limit."
        messages: list[BetaMessageParam] = [{"role": "user", "content": prompt}]
        schema = cast(dict[str, object], self._schema(case, focus or list(env["threads"])))
        output: BetaOutputConfigParam = {"effort": self.effort, "format": {"type": "json_schema", "schema": schema}}
        resp = self.client.beta.messages.create(
            model=self.model,
            max_tokens=cfg["max_tokens"],
            system=system,
            messages=messages,
            output_config=output,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            timeout=cfg["timeout_s"],
        )
        latency = int((time.monotonic() - t0) * 1000)
        if resp.stop_reason in ("refusal", "max_tokens"):
            raise ValueError(f"stop_reason {resp.stop_reason}")
        text = next(b.text for b in resp.content if b.type == "text")
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("reply is not a JSON object")
        u = resp.usage
        log.info(
            "Claude decided in %d ms | tokens in %s (cache read %s, write %s) out %s",
            latency,
            u.input_tokens,
            getattr(u, "cache_read_input_tokens", None),
            getattr(u, "cache_creation_input_tokens", None),
            u.output_tokens,
        )
        return cast(JSONObject, data), latency

    def _render(
        self, case: JSONObject, threads: Threads, env: Envelope, tel: dict[str, Telemetry], secs: float | None
    ) -> str:
        assert self.state is not None
        hist_n = config()["llm"]["history_messages"]
        out = [
            f"TIME: {'no wave clock' if secs is None else f'{secs:.0f} s left in the wave'}; "
            f"case progress {env['progress']:.0%} (0% = opening, 100% = land the deal now).",
            f"C_open (score 0 line): {_eur(env['c_open'])}. Alternative without a deal: {_eur(env['c_alt'])}.",
        ]
        for sid, te in env["threads"].items():
            proto, t, levers = self.state["protocols"][sid], tel[sid], te["levers"]
            out += [
                f"\n=== SUPPLIER {sid} ===",
                f"PROTOCOL: {proto['segment'].get('label')} - {proto['segment'].get('guidance')}",
                f"CULTURE ({proto['country'] or 'unknown'}): "
                f"{proto['culture']['label']} - {proto['culture']['guidance']}",
                "ENVELOPE: "
                + f"standing {te['sheet_id']} {json.dumps(te['standing_terms'])} -> C {_eur(te['c_standing'])}"
                + (
                    f", incl. est. supplier-health charge {_eur(te['c_true_standing'])}"
                    if te["penalty_at_offer"]
                    else ""
                )
                + f"; estimated supplier floor price {te['price_floor_est'] or 'unknown'}"
                + (
                    f" (calibrated on revealed results: {te['floor_ratio']:+.1%} vs its opening)"
                    if te["floor_ratio"] is not None
                    else ""
                )
                + f"; TARGET this round: {json.dumps(te['target_terms'])} -> C {_eur(te['c_target'])}.",
                "SUPPLIER OFFERS (every sheet of its latest message, our C; only the first can be accepted - "
                "propose a cheaper alternative back as your term sheet to get it): "
                + "; ".join(f"{o['sheet_id']} {json.dumps(o['terms'])} -> C {_eur(o['c'])}" for o in te["offers"]),
                self._packages(case, te),
                f"COVERAGE: their standing sheet covers {self._pct(te['coverage_pct'])} of our need over the "
                f"horizon; the uncovered part costs {_eur(te['uncovered_eur'])} at the fallback price. "
                f"Our target covers {self._pct(te['target_coverage_pct'])}.",
                f"POSITION: {env['position']} - {config()['leverage']['guidance'].get(env['position'], '')}",
                *([block] if (block := self._swaps_block(sid)) else []),
                "LEVERS (EUR change in our C vs. their standing sheet, same price; negative = saves us): "
                + "; ".join(f"{lv['field']}={option_label(lv['value'])}: {lv['delta_eur']:+,.0f}" for lv in levers),
                (
                    f"TELEMETRY: status {t['status']}, mindset {t['mindset']}, concession velocity "
                    f"{t['concession_velocity']}% of C_open per round, {t['moves_left']} messages left, "
                    f"claim verdicts so far {json.dumps(t['claims'])}."
                    if config()["mindset_inference"]["enabled"]
                    else f"TELEMETRY: status {t['status']}, {t['moves_left']} messages left, "
                    f"claim verdicts so far {json.dumps(t['claims'])}."
                ),
            ]
            if owner_run(threads[sid]):
                out.append("OWNER-RUN supplier: it values fast payment - keep the TARGET's short payment term.")
            elif distressed(self.pkg, sid):
                out.append(
                    "CASH-SHORT supplier (Sunday release: credit cut / lost customer / payment letter): fast payment "
                    "and firm volume are worth more to it than price - keep the TARGET's short payment term."
                )
            paced = self._min_counter_c(case, threads[sid], te)
            if paced is not None and te["target_terms"] is not None and te["c_standing"] is not None:
                floor, prev = paced
                at_target = price_for_cost(
                    case, te["target_terms"], min(floor, te["c_standing"] - 0.01), te["standard"]
                )
                held = floor <= safe_cost(case, prev, te["standard"]) + 0.01
                out.append(
                    (
                        "PACING: the supplier did not move since our last counter - hold: repeat or barely move our "
                        f"previous counter {json.dumps(prev)}, argue with the new evidence, never go below it; "
                        "keep terms we already matched with the supplier."
                    )
                    if held
                    else (
                        "PACING (suppliers do not concede without a move from us): your counter must cost us at "
                        f"least C {_eur(floor)} - at the TARGET's terms a unit price of at least {_eur(at_target)}; "
                        f"never below our previous counter {json.dumps(prev)}; keep terms we already matched with "
                        "the supplier."
                    )
                )
            brief = self.state["briefs"].get(sid)
            if config()["claims"]["enabled"]:
                nxt = self._next_claim(sid, env)
                out.append(
                    f"EVIDENCE THIS TURN (Python adds it to your e-mail; refer to it in words, no IDs): "
                    f"{nxt['sentence'] if nxt else 'none left - argue with the package, not new data'}"
                )
                if brief:
                    news = self._news_items(sid)
                    if news:
                        out.append("NEWS (news_to_cite candidates): " + "; ".join(f"{k}: {v}" for k, v in news.items()))
                    context = [i["sentence"] for i in brief["items"] if not i["refs"]]
                    if context:
                        out.append("BACKGROUND (context only): " + " ".join(context))
            elif brief:
                out.append("EVIDENCE (copy figures exactly):")
                for item in brief["items"]:
                    fav = item["favourable"]
                    ref_price = item.get("price")
                    if item["kind"] in PRICE_EVIDENCE and te["standing_price"] and ref_price:
                        # a quote or cost below the live offer argues for us; above it, against us
                        fav = ref_price < te["standing_price"] * PRICE_EVIDENCE[item["kind"]]
                    if item["refs"] and set(item["refs"]) <= self.cited:
                        continue
                    tag = (
                        "context-only"
                        if not item["refs"]
                        else ("favourable" if fav else "NOT favourable - do not cite")
                    )
                    out.append(f"- [{tag}] {item['sentence']}")
            out.append(f"THREAD (last {hist_n} messages):")
            for m in threads[sid][-hist_n:]:
                head = {k: m.get(k) for k in ("status", "term_sheets", "claim_results", "missing_fields") if m.get(k)}
                out.append(f"--- {m.get('from')}: {json.dumps(head)}\n{str(m.get('body') or '')[:900]}")
                for att in m.get("attachments") or []:  # type: ignore[union-attr]
                    if not isinstance(att, dict):
                        continue
                    aid = str(att.get("attachment_id") or att.get("name"))
                    if aid in self.shown_attachments:  # sent once: saves tokens on every later turn
                        out.append(f"[attachment {att.get('name')} - shown in an earlier turn]")
                        continue
                    self.shown_attachments.add(aid)
                    out.append(f"[attachment {att.get('name')}]\n{str(att.get('text') or '')[:1200]}")
        out.append(f"\nALREADY CITED (never cite again): {sorted(self.cited) or 'none'}")
        out.append("Decide the next move now.")
        return "\n".join(out)

    @staticmethod
    def _pct(v: float | None) -> str:
        return "unknown" if v is None else f"{v:.0%}"

    def _packages(self, case: JSONObject, te: ThreadEnvelope) -> str:
        """Linked demands made visible: the supplier's own structure at our target price vs. our best
        package at the same price - the difference is what its non-price demands cost us."""
        if te["target_price"] is None or not te["standing_terms"]:
            return "PACKAGES: -"
        theirs = complete_offer(case, {**te["standing_terms"], "unit_price": te["target_price"]})
        c_theirs = safe_cost(case, theirs, te["standard"], te["supplier_estimate"])
        lines = [
            f"their structure at our target price {json.dumps(theirs)} -> C {_eur(c_theirs)}",
            f"our best package at that price {json.dumps(te['target_terms'])} -> C {_eur(te['c_target'])}",
        ]
        return "PACKAGES (same price, different non-price terms): " + "; ".join(lines)

    def _close(self, case: JSONObject, threads: Threads, env: Envelope) -> JSONObject:
        """Time-cap close on the cheapest sheet (incl. alternatives) that beats the alternative,
        else the kit's closing move (walk away)."""
        alt = env["c_alt"]
        best = None
        for sid, te in env["threads"].items():
            c = te["c_true_standing"]
            if te["sheet_id"] and c is not None and (alt is None or c < alt):
                if must_haves_ok(case, te["standing_terms"], te["standard"]) and (best is None or c < best[0]):
                    best = (c, sid, te["sheet_id"])
        if best is None:
            return closing_move(case, threads)
        return {"supplier_id": best[1], "message": {"action": {"type": "accept", "term_sheet_id": best[2]}}}

    # -- v3 swap engine (swaps.py) --------------------------------------------------------------

    def _prepare_swaps(self, case: JSONObject, threads: Threads, env: Envelope, tel: dict[str, Telemetry]) -> None:
        cfg = config()["swaps"]
        self.swaps, self.mandatory = {}, {}
        if not cfg["enabled"]:
            return
        for sid, te in env["threads"].items():
            events = threads.get(sid, [])
            found = swap_engine.swaps(case, te, events, cfg)
            if not found:
                continue
            self.swaps[sid] = found
            sent = sum(m.get("from") == "buyer" for m in events)
            asked = swap_engine.wants(events, cfg, last_n=1) & {s["field"] for s in found}
            read = config()["mindset_inference"]["enabled"]  # quarantine: no stall-triggered trades
            if (read and swap_engine.stalled(tel[sid]["concession_velocity"], sent, cfg)) or (sent >= 1 and asked):
                must = next((s for s in found if s["field"] in asked), found[0])
                # a forced trade obeys the concession guard too (live P11: a swap priced off the
                # supplier's 50.00 jumped our counter 43.90 -> 48.99, accepted at once: 0.15)
                cap = self._counter_cap(case, events, te, tel[sid], env["progress"])
                if cap is None or must["c_true"] <= cap:
                    self.mandatory[sid] = must
                else:
                    log.info("swap %s=%s not forced: concedes past the guard", must["field"], must["value"])

    @staticmethod
    def _has_sheet(sheets: list[JSONValue], terms: JSONObject) -> bool:
        return any(isinstance(x, dict) and x.get("terms") == terms for x in sheets)

    def _swaps_block(self, sid: str) -> str:
        found = self.swaps.get(sid)
        if not found:
            return ""
        must = self.mandatory.get(sid)
        lines = []
        for s in found:
            tag = "MANDATORY this turn" if s is must else ("they asked" if s["wanted"] else "free for us")
            lines.append(
                f"[{tag}] give {s['field']}={option_label(s['value'])} for unit price EUR {s['ask_price']:,.2f} "
                f"(-{s['cut_pct']:.1f}%; our break-even EUR {s['breakeven_per_unit']:,.2f}/unit) -> sheet "
                f"{json.dumps(s['sheet'])}, C {_eur(s['c_true'])}"
            )
        return "SWAPS (Python-priced trades): " + " ; ".join(lines)

    def _note_swap(self, d: JSONObject) -> None:
        sid = str(d.get("supplier_id"))
        msg = d.get("message")
        must = self.mandatory.get(sid)
        if must is None or not isinstance(msg, dict):
            return
        sheets = msg.get("term_sheets")
        if not isinstance(sheets, list) or not self._has_sheet(sheets, must["sheet"]):
            return
        audit = msg.get("reasoning_audit")
        if isinstance(audit, dict) and isinstance(audit.get("mathematical_justification"), str):
            be_pct = must["breakeven_per_unit"] / must["ask_price"] * 100 if must["ask_price"] else 0.0
            audit["mathematical_justification"] = (
                str(audit["mathematical_justification"])
                + f" | swap offered: {must['field']}={option_label(must['value'])} for -{must['cut_pct']:.1f}%"
                + f" (break-even -{be_pct:.1f}%)"
            )

    # -- Python gates --------------------------------------------------------------------------

    def _validate(
        self,
        case: JSONObject,
        threads: Threads,
        env: Envelope,
        tel: dict[str, Telemetry],
        raw: JSONObject,
        latency: int,
    ) -> JSONObject | None:
        assert self.state is not None
        audit, dec = raw.get("reasoning_audit"), raw.get("decision")
        if not isinstance(audit, dict) or not isinstance(dec, dict):
            return None
        sid, action = str(dec.get("supplier_id")), str(dec.get("action"))
        te = env["threads"].get(sid)
        if te is None:
            return None
        sheets: list[JSONObject] = []
        for s in dec.get("term_sheets") or []:  # type: ignore[union-attr]
            if isinstance(s, dict):
                labels = self.state["labels"]
                sheets.append({k: (labels[k].get(str(v), v) if k in labels else v) for k, v in s.items()})
        kit_d = {
            "supplier_id": sid,
            "action": action,
            "subject": dec.get("subject"),
            "body": dec.get("outbound_email_text"),
            "term_sheets": sheets,
        }
        guarded = super().guard(case, threads, kit_d)  # type: ignore[no-untyped-call]
        if not isinstance(guarded, dict):
            return None
        d = cast(JSONObject, guarded)
        observed, intent = str(audit.get("observed_barrier") or ""), str(audit.get("strategic_intent") or "")
        t = tel[sid]

        if action == "accept":
            c, target = te["c_true_standing"], te["c_target"]
            late = (
                t["mindset"] in ("stalled", "critical_breakoff")
                or t["status"] in ("agreed", "final_offer")  # stated facts: Claude may take them
                or t["moves_left"] <= 1
                or env["progress"] >= 0.85
            )
            if self._partial_negotiable(case, te) and t["moves_left"] > 1 and t["status"] != "final_offer":
                log.info("accept vetoed: the sheet covers only %s of our need", te["coverage_pct"])
                return None  # counter with full coverage (the target sheet)
            if c is None or (target is not None and c > target * 1.002 and not late):
                log.info("accept vetoed: C %s above target %s and the case is not late", c, target)
                return None  # deterministic counter instead
            msg = d.get("message")
            action_obj = msg.get("action") if isinstance(msg, dict) else None
            if isinstance(action_obj, dict) and te["sheet_id"]:
                action_obj["term_sheet_id"] = te["sheet_id"]  # the main sheet: the only acceptable one
        elif action == "walk_away":
            alt = env["c_alt"]
            offers = [x["c_true_standing"] for x in env["threads"].values() if x["c_true_standing"] is not None]
            if alt is None or any(c < alt for c in offers):
                log.info("walk_away vetoed: an offer beats the alternative")
                return None
        else:
            msg = d.get("message")
            if not isinstance(msg, dict):
                return None
            kept: list[JSONValue] = []
            for s in msg.get("term_sheets") or []:  # type: ignore[union-attr]
                raw_terms = s.get("terms") if isinstance(s, dict) else None
                if not isinstance(raw_terms, dict):
                    continue
                terms = self._full_coverage(case, cast(JSONObject, raw_terms), te)
                c = safe_cost(case, terms, te["standard"], te["supplier_estimate"])
                if te["c_true_standing"] is None or c < te["c_true_standing"]:
                    kept.append({**cast(JSONObject, s), "terms": terms})
            allowance = self._counter_cap(case, threads.get(sid, []), te, t, env["progress"])
            if allowance is not None and kept:
                within: list[JSONValue] = []
                for x in kept:
                    sheet_terms = x.get("terms") if isinstance(x, dict) else None
                    if isinstance(sheet_terms, dict):
                        cost = safe_cost(case, sheet_terms, te["standard"], te["supplier_estimate"])
                        if cost <= allowance:
                            within.append(x)
                if not within:
                    log.info("Claude's sheets concede more than allowed this early - deterministic counter")
                    return None  # the fallback counter keeps e-mail text and sheet consistent
                kept = within
            if not kept:
                # no sheet of Claude's survived: never slip another sheet under its e-mail text
                log.info("no Claude sheet passed the gates - deterministic counter")
                return None
            sheets_out: list[JSONValue] = self._equivalent(case, te, kept)[:3]
            must = self.mandatory.get(sid)
            if must is not None and not self._has_sheet(sheets_out, must["sheet"]):
                trade: JSONValue = {"terms": must["sheet"]}
                sheets_out = [trade, *sheets_out][:3]  # the trade goes first
            msg["term_sheets"] = sheets_out
        return self._with_audit(case, d, env, tel, "claude", observed, intent, latency)

    def _coverage_fields(self, case: JSONObject) -> list[str]:
        neg = case.get("negotiable")
        return [f for f in ("contract_months", "volume_per_year") if isinstance(neg, list) and f in neg]

    def _partial_negotiable(self, case: JSONObject, te: ThreadEnvelope) -> bool:
        """The standing sheet leaves need uncovered and months / volume are still negotiable."""
        cov = te["coverage_pct"]
        return cov is not None and cov < 0.999 and bool(self._coverage_fields(case))

    def _full_coverage(self, case: JSONObject, terms: JSONObject, te: ThreadEnvelope) -> JSONObject:
        """A counter-sheet repaired to cover the whole need over the horizon - kept only when the
        cost function says it is cheaper for us (uncovered need costs the fallback price + risk)."""
        cov, _ = coverage(case, terms, te["standard"])
        fields = self._coverage_fields(case)
        buyer = case.get("buyer")
        if cov is None or cov >= 0.999 or not fields or not isinstance(buyer, dict):
            return terms
        need, horizon = buyer.get("need_per_year"), buyer.get("horizon_years")
        if not isinstance(need, int | float) or not isinstance(horizon, int | float):
            return terms
        opts = case.get("term_options") if isinstance(case.get("term_options"), dict) else {}
        repaired: JSONObject = dict(terms)
        wanted = {"contract_months": horizon * 12, "volume_per_year": need}
        for f in fields:
            options = opts.get(f) if isinstance(opts, dict) else None
            nums = sorted(o for o in options if isinstance(o, int | float)) if isinstance(options, list) else []
            fit = [o for o in nums if o >= wanted[f]]
            repaired[f] = fit[0] if fit else (nums[-1] if nums else wanted[f])
        repaired = complete_offer(case, repaired)
        if safe_cost(case, repaired, te["standard"], te["supplier_estimate"]) < safe_cost(
            case, terms, te["standard"], te["supplier_estimate"]
        ):
            log.info("counter-sheet repaired to full coverage: %s", repaired)
            return repaired
        return terms

    def _rule_walk(self, env: Envelope, tel: dict[str, Telemetry]) -> JSONObject | None:
        """Every live supplier made its final offer and each costs at least our alternative:
        walking away scores better than any of these deals (strong_factors_plus.txt)."""
        alt = env["c_alt"]
        if alt is None or not env["threads"]:
            return None
        for sid, te in env["threads"].items():
            c = te["c_true_standing"]
            if tel[sid]["status"] != "final_offer" or c is None or c < alt:
                return None
        sid = next(iter(env["threads"]))
        return {"supplier_id": sid, "message": {"action": {"type": "walk_away"}}}

    def _counter_cap(
        self, case: JSONObject, events: list[Message], te: ThreadEnvelope, t: Telemetry, progress: float
    ) -> float | None:
        """The dearest C any counter-sheet may have now: the concession guard, widened so it never
        forbids the concession path (Claude may concede up to twice the path's minimum step)."""
        allowance = self._concession_allowance(te, t, progress)
        paced = self._min_counter_c(case, events, te)
        if allowance is not None and paced is not None:
            c_prev = safe_cost(case, paced[1], te["standard"])
            allowance = max(allowance, paced[0] + (paced[0] - c_prev))
        return allowance

    @staticmethod
    def _concession_allowance(te: ThreadEnvelope, t: Telemetry, progress: float) -> float | None:
        """The dearest C a counter-sheet may have now: our target plus a share of the gap to the
        supplier's standing sheet that grows with the case (P11: Claude dropped a EUR 10.7k
        chargeback for EUR 1; P02: it offered the supplier's own price on turn 2). Not near the end."""
        target, standing = te["c_target"], te["c_true_standing"]
        if target is None or standing is None or standing <= target:
            return None
        if t["moves_left"] <= 2 or t["status"] == "final_offer":
            return None  # closing must never be blocked
        cfg = config()["concession_guard"]
        share = min(1.0, cfg["start_share"] + cfg["span_share"] * progress)
        return target + (standing - target) * share

    def _equivalent(self, case: JSONObject, te: ThreadEnvelope, sheets: list[JSONValue]) -> list[JSONValue]:
        """Multiple sheets must be equivalent for us (MESO): a supplier will pick the one it likes
        best, so a dearer 'option B' is a concession in disguise. Keep those within the tolerance
        of the cheapest one."""
        priced = []
        for s in sheets:
            terms = s.get("terms") if isinstance(s, dict) else None
            if isinstance(terms, dict):
                priced.append((safe_cost(case, terms, te["standard"], te["supplier_estimate"]), s))
        if not priced:
            return sheets
        cheapest = min(c for c, _ in priced)
        tol = config()["llm"]["equivalent_sheet_pct"] / 100
        kept = [s for c, s in priced if c <= cheapest * (1 + tol)]
        if len(kept) < len(priced):
            log.info("dropped %d non-equivalent sheet(s)", len(priced) - len(kept))
        return kept

    def _fallback(
        self,
        case: JSONObject,
        threads: Threads,
        env: Envelope,
        tel: dict[str, Telemetry],
        sid: str | None = None,
        reason: str = "No model answer this turn.",
    ) -> JSONObject:
        """No Claude (timeout, outage, vetoed move) or a thread to keep alive: counter at the
        engine's target sheet."""
        sid = sid or env["best_supplier"] or next(iter(env["threads"]), None)
        if sid is None:
            return closing_move(case, threads)
        te, t = env["threads"][sid], tel[sid]
        if te["target_terms"] is None or t["moves_left"] <= 1 or t["mindset"] == "critical_breakoff":
            d = self._close(case, threads, env)
            return self._with_audit(case, d, env, tel, "fallback", "Last chance to close.", "Close on the best sheet.")
        must = self.mandatory.get(sid)  # an engine-priced trade, if one is due, beats the plain target
        terms = complete_offer(case, must["sheet"] if must is not None else te["target_terms"])
        price = _num(terms.get("unit_price"))
        body = (
            "Dear Sir or Madam,\n\nthank you for your offer. To move forward we propose the attached terms"
            + (f", at a unit price of EUR {price:,.2f}" if price is not None else "")
            + ". We would appreciate your confirmation.\n\nKind regards,\n"
            + SIGNATURE
        )
        title = case.get("title")
        d = {
            "supplier_id": sid,
            "message": {"subject": f"Re: {title}", "body": body, "term_sheets": [{"terms": terms}]},
        }
        return self._with_audit(case, d, env, tel, "fallback", reason, "Counter at the engine's target sheet.")

    # -- audit ---------------------------------------------------------------------------------

    def _with_audit(
        self,
        case: JSONObject,
        d: JSONObject,
        env: Envelope,
        tel: dict[str, Telemetry],
        source: DecisionSource,
        observed: str,
        intent: str,
        latency: int | None = None,
    ) -> JSONObject:
        assert self.state is not None
        sid = str(d.get("supplier_id"))
        msg = d.get("message")
        if not isinstance(msg, dict) or sid not in env["threads"]:
            return d
        te, t, proto = env["threads"][sid], tel[sid], self.state["protocols"][sid]
        msg["reasoning_audit"] = {
            "observed_barrier": observed or "-",
            "strategic_intent": intent or "-",
            "mathematical_justification": self._maths(case, te, t, env, msg),
            "decision_source": source,
            "concession_velocity": t["concession_velocity"],
            "supplier_mindset": t["mindset"],
            "c_target": te["c_target"],
            "c_floor_est": te["c_floor_est"],
            "penalty_at_offer": te["penalty_at_offer"],
            "claims": cast(JSONValue, t["claims"]),
            "llm_latency_ms": latency,
            "seconds_left": self._seconds_left(),
            "c_open": env["c_open"],
            "c_alt": env["c_alt"],
            "segment_protocol": proto["segment"].get("label"),
            "culture_protocol": proto["culture"]["label"],
        }
        return d

    def _maths(self, case: JSONObject, te: ThreadEnvelope, t: Telemetry, env: Envelope, msg: Message) -> str:
        """The audit's numbers, all from the engine."""
        sheets = msg.get("term_sheets")
        first = sheets[0] if isinstance(sheets, list) and sheets else None
        ours = first.get("terms") if isinstance(first, dict) else None
        c_ours = safe_cost(case, ours, te["standard"], te["supplier_estimate"]) if isinstance(ours, dict) else None
        best = min(te["levers"], key=lambda lv: lv["delta_eur"], default=None)
        parts = [
            f"C_open {_eur(env['c_open'])}",
            f"supplier standing {_eur(te['c_standing'])}"
            + (f" (+{_eur(te['penalty_at_offer'])} est. supplier-health charge)" if te["penalty_at_offer"] else ""),
            f"our proposal {_eur(c_ours)}" if c_ours is not None else "no counter-sheet",
            f"target {_eur(te['c_target'])}",
            f"floor estimate {_eur(te['c_floor_est'])}"
            + (f" (calibrated {te['floor_ratio']:+.1%})" if te["floor_ratio"] is not None else ""),
            f"alternative {_eur(env['c_alt'])}",
            f"position {env['position']}"
            + (f" (alt {env['leverage_gap_pct']:+.1f}% vs C_open)" if env["leverage_gap_pct"] is not None else ""),
        ]
        if best and best["delta_eur"] < 0:
            parts.append(f"best lever {best['field']}={option_label(best['value'])} saves {_eur(-best['delta_eur'])}")
        if t["concession_velocity"] is not None:
            parts.append(f"concession velocity {t['concession_velocity']}%/round ({t['mindset']})")
        if te["coverage_pct"] is not None and te["coverage_pct"] < 0.999:
            parts.append(f"supplier sheet covers {te['coverage_pct']:.0%} (uncovered {_eur(te['uncovered_eur'])})")
        return " | ".join(parts) + "."

    def _remember_citations(self, d: JSONObject) -> None:
        msg = d.get("message")
        body = msg.get("body") if isinstance(msg, dict) else None
        if isinstance(body, str):
            self.cited |= set(ID_RE.findall(body))


def new_agent_factory(pkg: Package | None) -> Callable[[Callable[[], float | None] | None], HollerauAgent]:
    """One Anthropic client shared by all cases; one agent per case, each with its wave deadline."""
    client = anthropic.Anthropic(max_retries=1)
    return lambda deadline: HollerauAgent(client, pkg, deadline=deadline)
