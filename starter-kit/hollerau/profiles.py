"""Strategy configuration (config/strategy.json) and the per-case protocols it yields.

Segment protocol: from the case's category_goal (leverage / stabilise / secure_supply / ...).
Culture protocol: from the supplier's country in the data package.
"""

import json
from functools import cache
from pathlib import Path
from typing import TypedDict, cast

CONFIG = Path(__file__).parent / "config" / "strategy.json"
CALIBRATION = Path(__file__).parent / "config" / "calibration.json"
DEFAULT_SEGMENT = "routine"
DEFAULT_CULTURE = "_default"


class SegmentConfig(TypedDict, total=False):
    label: str
    relationship: bool
    guidance: str
    # leverage-style targets (percent)
    anchor_below_floor_pct: float
    anchor_below_offer_pct: float
    landing_above_floor_pct: float
    landing_below_offer_pct: float
    min_margin_pct: float
    # relationship-style targets (percent)
    anchor_below_target_pct: float
    max_discount_from_offer_pct: float  # never ask more than this below the supplier's offer


class CultureConfig(TypedDict):
    label: str
    guidance: str


class TelemetryConfig(TypedDict):
    stalled_velocity_pct: float
    yielding_velocity_pct: float


class LLMConfig(TypedDict):
    timeout_s: float
    max_tokens: int
    history_messages: int
    equivalent_sheet_pct: float  # MESO tolerance: extra sheets within this % of the cheapest
    keepalive_s: float  # answer a waiting thread before this (60 s rule, 3 strikes)


class PriceSearchConfig(TypedDict):
    low_pct_of_offer: float
    steps: int


class FullCostConfig(TypedDict):
    use_lower_bound: bool


class LeverageConfig(TypedDict):
    vulnerable_above_pct: float  # alternative more than this % above C_open (or none) = vulnerable
    aggressiveness: dict[str, float]  # position -> anchor-depth factor
    vulnerable_landing_pct: float  # vulnerable: land this % softer
    guidance: dict[str, str]  # position -> prompt guidance


class SwapsConfig(TypedDict):
    enabled: bool
    premium: float  # ask this multiple of our break-even price cut
    max_cut_pct: float  # never ask more than this % off the supplier's price
    trigger_velocity_pct: float  # a concession step below this % of C_open counts as a stall
    default_ask_pct: dict[str, float]  # per lever: the doc's default ask (% of price)
    default_ask_eur: dict[str, float]  # per lever: default ask in EUR per unit
    want_patterns: dict[str, list[str]]  # per lever: supplier wording that signals it wants it


class PacingConfig(TypedDict):
    hold_until_progress: float


class FloorPacingConfig(TypedDict):
    enabled: bool
    steps: list[list[float]]  # [[our message number up to, share of the envelope], ...]


class GoalFit(TypedDict):
    floor_ratio: float  # real floor price / opening price - 1, fitted on revealed c_best
    n: int
    min: float
    max: float
    cases: list[str]


class AlternativesConfig(TypedDict):
    min_gain_eur: float
    min_gain_pct: float


class StrategyConfig(TypedDict):
    segments: dict[str, SegmentConfig]
    cultures: dict[str, CultureConfig]
    country_cost_factor: dict[str, float]
    full_cost_estimate: FullCostConfig
    relationship_price_search: PriceSearchConfig
    telemetry: TelemetryConfig
    leverage: LeverageConfig
    swaps: SwapsConfig
    pacing: PacingConfig
    floor_pacing: FloorPacingConfig
    alternatives: AlternativesConfig
    lever_friction_pct: float  # % of price per changed non-price term: suppliers price our demands back in
    friction_fields: list[str]  # the terms friction applies to (not coverage / quality)
    llm: LLMConfig


class Protocol(TypedDict):
    goal: str
    segment: SegmentConfig
    country: str | None
    culture: CultureConfig


@cache
def config() -> StrategyConfig:
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    missing = set(StrategyConfig.__annotations__) - set(raw)
    if missing:
        raise ValueError(f"{CONFIG} misses {sorted(missing)}")
    return cast(StrategyConfig, raw)


@cache
def calibration() -> dict[str, GoalFit]:
    """Floor ratios per category_goal fitted by `python -m hollerau.calibrate` ({} if not fitted)."""
    if not CALIBRATION.exists():
        return {}
    return cast(dict[str, GoalFit], json.loads(CALIBRATION.read_text(encoding="utf-8")))


def protocol(category_goal: str | None, country: str | None) -> Protocol:
    cfg = config()
    goal = category_goal if category_goal in cfg["segments"] else DEFAULT_SEGMENT
    culture = cfg["cultures"].get(country or "", cfg["cultures"][DEFAULT_CULTURE])
    return {"goal": goal, "segment": cfg["segments"][goal], "country": country, "culture": culture}
