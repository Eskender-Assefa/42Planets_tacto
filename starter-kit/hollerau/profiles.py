"""Strategy configuration (config/strategy.json) and the per-case protocols it yields.

Segment protocol: from the case's category_goal (leverage / stabilise / secure_supply / ...).
Culture protocol: from the supplier's country in the data package.
"""

import json
from functools import cache
from pathlib import Path
from typing import TypedDict, cast

CONFIG = Path(__file__).parent / "config" / "strategy.json"
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


class PriceSearchConfig(TypedDict):
    low_pct_of_offer: float
    steps: int


class FullCostConfig(TypedDict):
    use_lower_bound: bool


class StrategyConfig(TypedDict):
    segments: dict[str, SegmentConfig]
    cultures: dict[str, CultureConfig]
    country_cost_factor: dict[str, float]
    full_cost_estimate: FullCostConfig
    relationship_price_search: PriceSearchConfig
    telemetry: TelemetryConfig
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


def protocol(category_goal: str | None, country: str | None) -> Protocol:
    cfg = config()
    goal = category_goal if category_goal in cfg["segments"] else DEFAULT_SEGMENT
    culture = cfg["cultures"].get(country or "", cfg["cultures"][DEFAULT_CULTURE])
    return {"goal": goal, "segment": cfg["segments"][goal], "country": country, "culture": culture}
