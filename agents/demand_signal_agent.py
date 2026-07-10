"""
Demand Signal Agent.

A sub-agent responsible for one job: given a sector, a set of HS codes,
and target countries, fetch import demand data and turn it into a
structured signal — growth rate, surge flag, competition density — that
the main orchestrator agent can use to compute opportunity scores.

This is implemented as a deterministic function rather than an LLM call.
See the README for why: this is a data-fetch-and-compute job with no
ambiguity to reason through, so an LLM loop here would only add latency
and cost. It still follows the "agent" contract (typed input, typed
output, can be swapped for an LLM-backed version later) so the
orchestrator doesn't need to know the difference.
"""

from dataclasses import dataclass, field

from data_sources.mock_trade_api import fetch_import_data


@dataclass
class DemandSignal:
    hs_code: str
    destination_country: str
    sector: str
    growth_rate_pct: float
    surge_detected: bool
    active_indian_suppliers: int
    competition_density_score: float  # 0-1, higher = more crowded
    latest_monthly_volume_usd: float
    data_source: str
    as_of: str


@dataclass
class DemandSignalAgentOutput:
    sector: str
    signals: list[DemandSignal] = field(default_factory=list)

    def top_signal(self) -> DemandSignal | None:
        if not self.signals:
            return None
        return max(self.signals, key=lambda s: s.growth_rate_pct)


# Above this monthly growth rate, we flag a "surge" worth prioritizing.
SURGE_THRESHOLD_PCT = 15.0

# Caps active_indian_suppliers at this count for normalizing competition
# density to a 0-1 score. Tune this against real data once available.
COMPETITION_DENSITY_CAP = 20


def _competition_density(active_suppliers: int) -> float:
    return round(min(active_suppliers / COMPETITION_DENSITY_CAP, 1.0), 2)


def _growth_rate_from_volumes(monthly_volumes: list[dict]) -> float:
    if len(monthly_volumes) < 2:
        return 0.0
    first = monthly_volumes[0]["volume_usd"]
    last = monthly_volumes[-1]["volume_usd"]
    if first <= 0:
        return 0.0
    n_periods = len(monthly_volumes) - 1
    # Average monthly growth rate (CAGR-style) over the lookback window.
    growth = ((last / first) ** (1 / n_periods) - 1) * 100
    return round(growth, 2)


def run_demand_signal_agent(
    sector: str,
    hs_codes: list[str],
    target_countries: list[str],
    lookback_months: int = 6,
) -> DemandSignalAgentOutput:
    """
    The Demand Signal Agent's entry point. Fetches data for every
    (hs_code, country) pair in the cross product and returns structured
    signals for each.

    This is the function the orchestrator calls as a tool/node.
    """
    signals: list[DemandSignal] = []

    for hs_code in hs_codes:
        for country in target_countries:
            raw = fetch_import_data(
                hs_code=hs_code,
                destination_country=country,
                sector=sector,
                lookback_months=lookback_months,
            )
            growth_rate = _growth_rate_from_volumes(raw["monthly_volumes"])
            signals.append(
                DemandSignal(
                    hs_code=raw["hs_code"],
                    destination_country=raw["destination_country"],
                    sector=raw["sector"],
                    growth_rate_pct=growth_rate,
                    surge_detected=growth_rate >= SURGE_THRESHOLD_PCT,
                    active_indian_suppliers=raw["active_indian_suppliers"],
                    competition_density_score=_competition_density(
                        raw["active_indian_suppliers"]
                    ),
                    latest_monthly_volume_usd=raw["monthly_volumes"][-1][
                        "volume_usd"
                    ],
                    data_source=raw["data_source"],
                    as_of=raw["as_of"],
                )
            )

    return DemandSignalAgentOutput(sector=sector, signals=signals)
