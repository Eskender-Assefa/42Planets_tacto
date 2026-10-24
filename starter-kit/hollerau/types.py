"""Row shapes of the Supabase schema (db/migrations/001-003). Mirrors db/types.ts."""

from typing import Literal, NotRequired, TypedDict

Environment = Literal["sim", "practice", "final"]
CaseStatus = Literal["active", "deal", "walked_away", "no_deal", "error"]
MoveAction = Literal["send", "accept", "walk_away"]
DecisionSource = Literal["claude", "fallback", "rule", "closing", "naive"]


class IndexClause(TypedDict):
    series: str
    material_share: float
    deadband_pct: float
    base_month: str


class ClaimTally(TypedDict):
    verified: int
    irrelevant: int
    contradicted: int
    duplicate: int


class Terms(TypedDict, total=False):
    unit_price: float | None
    volume_per_year: int | None
    contract_months: int | None
    payment_days: int | None
    lead_time_days: int | None
    incoterm: str | None
    index_clause: IndexClause | None
    tooling_eur: float | None
    effective_date: str | None
    ppm_commitment: float | None
    chargeback_eur_per_complaint: float | None


class SupplierRow(TypedDict):
    id: str
    name: str
    country: str | None
    category: str | None
    abc_class: str | None


class CaseRow(TypedDict):
    """Insert shape of `cases`; DB-defaulted columns (status, started_at) may be omitted."""

    session_id: str
    case_id: str
    environment: Environment
    wave: NotRequired[int | None]
    title: NotRequired[str | None]
    case_type: NotRequired[str | None]
    category_goal: NotRequired[str | None]
    supplier_ids: NotRequired[list[str]]
    status: NotRequired[CaseStatus]
    deal_supplier_id: NotRequired[str | None]
    c_open: NotRequired[float | None]
    c_alt: NotRequired[float | None]
    c_best: NotRequired[float | None]
    c_deal: NotRequired[float | None]
    score: NotRequired[float | None]
    ended_at: NotRequired[str | None]
    segment_protocol: NotRequired[str | None]
    culture_protocol: NotRequired[str | None]


class CaseUpdate(TypedDict, total=False):
    """Columns the runner fills in during and at the end of a case."""

    status: CaseStatus
    deal_supplier_id: str | None
    c_open: float | None
    c_alt: float | None
    c_best: float | None
    c_deal: float | None
    score: float | None
    ended_at: str
    segment_protocol: str | None
    culture_protocol: str | None


class AuditLogRow(TypedDict):
    """Insert shape of `audit_logs`; id and created_at come from the DB."""

    session_id: str
    supplier_id: str
    turn_number: int
    action: MoveAction
    observed_barrier: str
    strategic_intent: str
    mathematical_justification: str
    seconds_left: NotRequired[int | None]
    supplier_terms: NotRequired[Terms | None]
    proposed_terms: NotRequired[Terms | None]
    c_supplier_offer: NotRequired[float | None]
    c_proposed: NotRequired[float | None]
    concession_velocity: NotRequired[float | None]
    supplier_mindset: NotRequired[str | None]
    message_subject: NotRequired[str | None]
    message_body: NotRequired[str | None]
    c_target: NotRequired[float | None]
    c_floor_est: NotRequired[float | None]
    penalty_at_offer: NotRequired[float | None]
    claims: NotRequired[ClaimTally | None]
    decision_source: NotRequired[DecisionSource | None]
    llm_latency_ms: NotRequired[int | None]
