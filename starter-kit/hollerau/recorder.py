"""Write-first traceability for arena_kit's play loop.

RecordingTable is a drop-in RemoteTable: every move arena_kit.play.play() sends - agent decisions
and the kit's own closing_move at a wave cap - goes through send() or close(). Both write the
move's audit row to Supabase FIRST; if that write fails, the move is not sent (DBError propagates
and play() stops). Costs come from arena_kit.cost.total_cost via hollerau.kit, never from the LLM.

An agent may attach its reasoning to a message as message["reasoning_audit"] =
{"observed_barrier", "strategic_intent", "mathematical_justification", plus optional telemetry:
"decision_source", "concession_velocity", "supplier_mindset", "c_target", "c_floor_est",
"penalty_at_offer", "claims", "llm_latency_ms", "seconds_left", "c_open", "c_alt",
"segment_protocol", "culture_protocol"}; it is logged and stripped before the message goes to the
arena. Without it (the naive agent, the kit's time-cap close) a labelled, deterministic text is
logged instead.
"""

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast, get_args

from arena_kit.client import ArenaClient
from arena_kit.play import RemoteTable

from .db import DBError, SupabaseDB
from .kit import JSONObject, JSONValue, Message, Threads, standard_terms, standing, total_cost
from .types import (
    AuditLogRow,
    CaseStatus,
    CaseUpdate,
    ClaimTally,
    DecisionSource,
    Environment,
    MoveAction,
    Terms,
)

log = logging.getLogger("hollerau.recorder")

REASONING_KEY = "reasoning_audit"
TERM_KEYS = frozenset(Terms.__annotations__)
NAIVE = "Naive baseline agent - no reasoning layer yet"


def to_terms(obj: JSONValue) -> Terms | None:
    """The known term-sheet fields of an arena terms object (others are ignored)."""
    if not isinstance(obj, dict) or not obj:
        return None
    return cast(Terms, {k: v for k, v in obj.items() if k in TERM_KEYS})


def _num(v: JSONValue) -> float | None:
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) else None


def _str(v: JSONValue) -> str | None:
    return v if isinstance(v, str) else None


def _eur(v: float | None) -> str:
    return "n/a" if v is None else f"€{v:,.2f}"


class RecordingTable(RemoteTable):  # upstream RemoteTable is unannotated: super() calls are marked
    def __init__(
        self,
        client: ArenaClient,
        db: SupabaseDB,
        environment: Environment,
        wave: int | None = None,
        case: JSONObject | None = None,
        deadline: Callable[[], float | None] | None = None,
        unreasoned: tuple[str, DecisionSource] = (NAIVE, "naive"),
    ) -> None:
        """`case`: the final's case listing (lets RemoteTable resume a started session).
        `deadline`: the wave cap as time.time() (final only) - recorded as seconds_left.
        `unreasoned`: label and source for moves that carry no reasoning (naive agent, or the
        kit's own closing_move at the wave cap when a reasoning agent plays)."""
        super().__init__(client, case)  # type: ignore[no-untyped-call]
        self.db, self.environment, self.wave, self.deadline = db, environment, wave, deadline
        self.unreasoned_label, self.unreasoned_source = unreasoned
        self.run_tag = time.strftime("%Y%m%dT%H%M%S")
        self.threads: Threads = {}
        self.case_data: JSONObject = {}
        self.db_session_id = ""
        self.case_meta_written = False

    def seconds_left(self) -> int | None:
        cap = self.deadline() if self.deadline else None
        return max(0, int(cap - time.time())) if cap else None

    # -- session -------------------------------------------------------------------------------

    def open(self, case_id: str) -> tuple[JSONObject, Threads]:
        case, threads = super().open(case_id)  # type: ignore[no-untyped-call]
        self.case_data, self.threads = case, threads  # same objects play() mutates
        arena_id = str(self.session_id)
        # the simulator restarts its session ids (sim1, sim2, ...) on every launch
        self.db_session_id = f"sim-{self.run_tag}-{arena_id}" if self.environment == "sim" else arena_id
        buyer = case.get("buyer")
        suppliers = case.get("suppliers")
        self.db.upsert_case(
            {
                "session_id": self.db_session_id,
                "case_id": case_id,
                "environment": self.environment,
                "wave": self.wave,
                "title": _str(case.get("title")),
                "case_type": _str(case.get("type")),
                "category_goal": _str(buyer.get("category_goal")) if isinstance(buyer, dict) else None,
                "supplier_ids": [str(s) for s in suppliers] if isinstance(suppliers, list) else list(threads),
            }
        )
        log.info("recording %s as %s", case_id, self.db_session_id)
        return case, threads

    def send(self, supplier_id: str, message: Message) -> JSONObject:
        clean = self._log_move(supplier_id, message, "send")
        return cast(JSONObject, super().send(supplier_id, clean))  # type: ignore[no-untyped-call]

    def close(self, supplier_id: str, message: Message) -> JSONObject:
        action = message.get("action")
        kind = action.get("type") if isinstance(action, dict) else None
        if kind == "accept" and isinstance(action, dict):
            main_id, _ = standing(self.threads.get(supplier_id, []))
            if main_id and action.get("term_sheet_id") != main_id:
                # the arena accepts only the standing (main) sheet: 422 otherwise, and play() would
                # lose the whole case (P10 in practice run 2)
                log.warning("accept of %s swapped to the standing sheet %s", action.get("term_sheet_id"), main_id)
                action["term_sheet_id"] = main_id
        clean = self._log_move(supplier_id, message, "accept" if kind == "accept" else "walk_away")
        return cast(JSONObject, super().close(supplier_id, clean))  # type: ignore[no-untyped-call]

    def finish(self, result: JSONObject) -> None:
        """Store the case's outcome. Called by the runner after play() returns."""
        try:
            state = cast(JSONObject, self.client.session(self.session_id))
        except Exception as e:  # the result itself is what matters; the end reason is a nicety
            log.warning("could not read end reason: %s", e)
            state = {}
        reason = _str(state.get("end_reason")) or _str(result.get("end_reason")) or ""
        status: CaseStatus = "deal" if result.get("deal") else ("walked_away" if "walk" in reason else "no_deal")
        changes: CaseUpdate = {
            "status": status,
            "deal_supplier_id": _str(result.get("supplier_id")),
            "c_open": _num(result.get("c_open")),
            "c_alt": _num(result.get("c_alt")),
            "c_best": _num(result.get("c_best")),
            "c_deal": _num(result.get("c_deal")),
            "score": _num(result.get("score")),
            "ended_at": datetime.now(UTC).isoformat(),
        }
        self.db.update_case(self.db_session_id, changes)

    # -- audit ---------------------------------------------------------------------------------

    def _write_case_meta(self, r: JSONObject) -> None:
        """Once per case, from the agent's first reasoned move: protocols and the live envelope's
        c_open / c_alt (the final result overwrites them with the arena's figures)."""
        changes: CaseUpdate = {
            "c_open": _num(r.get("c_open")),
            "c_alt": _num(r.get("c_alt")),
            "segment_protocol": _str(r.get("segment_protocol")),
            "culture_protocol": _str(r.get("culture_protocol")),
        }
        try:
            self.db.update_case(self.db_session_id, changes)
            self.case_meta_written = True
        except DBError as e:  # display data only: the move's own audit row is what must not fail
            log.warning("case meta not written: %s", e)

    def _cost(self, terms: JSONObject, standard: JSONObject) -> float | None:
        if _num(terms.get("unit_price")) is None:
            return None
        try:
            return round(total_cost(self.case_data, terms, standard), 2)
        except (KeyError, TypeError, ValueError) as e:
            log.warning("total_cost failed for %s: %s", terms, e)
            return None

    def _log_move(self, supplier_id: str, message: Message, action: MoveAction) -> Message:
        """Write the audit row; return the message without our private reasoning key."""
        events = self.threads.get(supplier_id, [])
        standard = standard_terms(events) if events else {}
        _, theirs = standing(events) if events else (None, {})
        sheets = message.get("term_sheets")
        first = sheets[0] if isinstance(sheets, list) and sheets else None
        ours: JSONObject = {}
        if isinstance(first, dict) and isinstance(first.get("terms"), dict):
            ours = cast(JSONObject, first["terms"])
        elif action == "accept":
            ours = theirs  # accepting = closing on the supplier's sheet - find the one accepted
            act = message.get("action")
            wanted = act.get("term_sheet_id") if isinstance(act, dict) else None
            last = next((m for m in reversed(events) if m.get("from") != "buyer"), None)
            for s in (last.get("term_sheets") if last else None) or []:  # type: ignore[union-attr]
                if isinstance(s, dict) and s.get("term_sheet_id") == wanted and isinstance(s.get("terms"), dict):
                    ours = cast(JSONObject, s["terms"])
        c_theirs, c_ours = self._cost(theirs, standard), self._cost(ours, standard)

        reasoning = message.get(REASONING_KEY)
        r = reasoning if isinstance(reasoning, dict) else {}
        source = _str(r.get("decision_source"))
        claims = r.get("claims")
        secs = _num(r.get("seconds_left"))
        latency = _num(r.get("llm_latency_ms"))
        row: AuditLogRow = {
            "session_id": self.db_session_id,
            "supplier_id": supplier_id,
            "turn_number": sum(m.get("from") == "buyer" for m in events) + 1,
            "action": action,
            "seconds_left": int(secs) if secs is not None else self.seconds_left(),
            "supplier_terms": to_terms(theirs),
            "proposed_terms": to_terms(ours) if action != "walk_away" else None,
            "c_supplier_offer": c_theirs,
            "c_proposed": c_ours if action != "walk_away" else None,
            "concession_velocity": _num(r.get("concession_velocity")),
            "supplier_mindset": _str(r.get("supplier_mindset")),
            "observed_barrier": _str(r.get("observed_barrier"))
            or (f"Supplier's standing offer costs {_eur(c_theirs)}." if c_theirs else "No standing term sheet."),
            "strategic_intent": _str(r.get("strategic_intent"))
            or f"{self.unreasoned_label}: {'counter-offer' if action == 'send' else action.replace('_', ' ')}.",
            "mathematical_justification": _str(r.get("mathematical_justification"))
            or f"total_cost: supplier offer {_eur(c_theirs)}, our proposal {_eur(c_ours)}.",
            "message_subject": _str(message.get("subject")),
            "message_body": _str(message.get("body")),
            "c_target": _num(r.get("c_target")),
            "c_floor_est": _num(r.get("c_floor_est")),
            "penalty_at_offer": _num(r.get("penalty_at_offer")),
            "claims": cast(ClaimTally, claims) if isinstance(claims, dict) else None,
            "decision_source": cast(DecisionSource, source)
            if source in get_args(DecisionSource)
            else (None if r else self.unreasoned_source),
            "llm_latency_ms": int(latency) if latency is not None else None,
        }
        if not self.case_meta_written and r:
            self._write_case_meta(r)
        try:
            self.db.insert_audit(row)
        except DBError as e:
            if e.status != 409:
                log.error("audit write failed - NOT sending the move: %s", e)
                raise
            # this turn was logged but the arena refused the move (409) and the agent decided again
            log.warning("re-logging turn %s with %s after a refused move", row["turn_number"], supplier_id)
            self.db.replace_audit(row)
        return {k: v for k, v in message.items() if k != REASONING_KEY}
