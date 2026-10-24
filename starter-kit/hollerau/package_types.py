"""Row shapes of the data package (data/package/world.sqlite) that the runner reads.

Column names are exactly the SQLite columns; values are as SQLite returns them (dates as ISO
strings, flags as 0/1 integers, semicolon-separated ID lists as strings).
"""

from typing import TypedDict


class PackageSupplier(TypedDict):
    id: str
    name: str
    country: str | None
    currency: str | None
    payment_days: int | None
    skonto_days: int | None
    skonto_pct: int | None
    incoterm: str | None
    created: str | None
    category: str | None
    detail: str | None  # 'full' (detailed supplier) | 'spend only' (long tail)
    blocked: int | None
    contract_id: str | None
    standard_lead_time_days: int | None
    abc_class: str | None


class SupplierIntel(TypedDict):
    supplier_id: str
    legal_form: str | None
    founded: int | None
    owner_type: str | None
    group_parent: str | None
    staff: int | None
    filed_fy: int | None
    turnover_eur: int | None
    turnover_band: str | None
    equity_ratio_pct: float | None
    credit_index: int | None
    credit_index_12m_ago: int | None
    vda63_grade: str | None
    certifications: str | None


class Part(TypedDict):
    id: str
    description: str | None
    category: str | None
    material_group: str | None
    grade: str | None
    net_weight_kg: float | None
    uom: str | None
    price_unit: int | None
    planned_lead_time_days: int | None
    pump_series: str | None
    standard_price: float | None
    status: str | None
    abc_class: str | None


class PriceCondition(TypedDict):
    part_id: str
    supplier_id: str
    valid_from: str | None
    price: float | None
    basis: str | None
    event_id: str | None
    valid_to: str | None
    price_unit: int | None
    currency: str | None


class Scorecard(TypedDict):
    id: str
    supplier_id: str
    quarter: str | None
    period_start: str | None
    period_end: str | None
    gr_lines: int | None
    otd_pct: float | None
    otd_confirmed_pct: float | None
    received_qty: int | None
    complaint_qty: int | None
    ppm: int | None
    qn_count: int | None
    open_8d_overdue: int | None
    score: float | None
    class_: str | None  # SQLite column `class` (renamed: Python keyword)
    colour: str | None


class NegotiationEvent(TypedDict):
    event_id: str
    date: str | None
    supplier_id: str
    part_id: str | None
    type: str | None
    asked_pct: float | None
    settled_pct: float | None
    note: str | None


class TriggerDocument(TypedDict):
    """A `documents` row plus its text (letter / e-mail / memo / RFQ from correspondence/)."""

    id: str
    date: str | None
    kind: str | None
    supplier_id: str | None
    part_ids: str | None
    subject: str | None
    author: str | None
    file: str | None
    asked_pct: float | None
    asked_price: float | None
    effective_date: str | None
    notice_days: int | None
    text: str


class ShouldCost(TypedDict):
    id: str  # 'cost:<part>' - citable
    part_id: str
    estimate_date: str | None
    cost_base: str | None  # country of the cost base, e.g. 'DE'
    supplier_id: str | None  # set when the estimate models this supplier's own plant
    unit_cost: float | None
    price_unit: int | None
    material_eur: float | None
    conversion_eur: float | None
    overhead_eur: float | None
    confidence_pct: int | None
    method: str | None


class CostDriver(TypedDict):
    part_id: str
    series_id: str
    weight: float | None
    source: str | None


class IndexValue(TypedDict):
    id: str  # 'idx:<series>@<YYYY-MM>' - citable
    series_id: str
    month: str
    value: float | None


class IndexSeries(TypedDict):
    id: str
    name: str | None
    unit: str | None
    source: str | None
    frequency: str | None
    licence: str | None
    url: str | None
    first_month: str | None
    last_month: str | None
    formula: str | None


class NewsItem(TypedDict):
    id: str
    date: str | None
    supplier_id: str | None
    topic: str | None
    headline: str | None
    body: str | None
    source: str | None


class SupplierBundle(TypedDict):
    """Everything the package says about one supplier and the part under negotiation."""

    supplier: PackageSupplier
    intel: SupplierIntel | None
    part: Part | None
    current_price: PriceCondition | None
    latest_scorecard: Scorecard | None
    negotiation_history: list[NegotiationEvent]


class SampleBundle(TypedDict):
    role: str  # 'leverage' | 'strategic' | 'baseline_email'
    case_id: str | None
    document: TriggerDocument | None
    bundle: SupplierBundle
