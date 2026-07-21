"""
Logistics Agent.

Pattern A from agents/_template_agent.py: deterministic fetch-and-
compute, like Demand Signal and Scheme/Compliance. There's no judgment
call here — freight cost, transit time, and customs complexity for a
given trade lane are lookup/normalization, not something that benefits
from an LLM call.

Output feeds directly into the opportunity scoring formula as
logistics_cost (0-1, higher = more expensive/complex = worse for
scoring), replacing the last remaining placeholder in scorer.py.
"""

from dataclasses import dataclass, field

from data_sources.logistics_data import get_logistics_data

# Normalization caps — values at or above these map to a logistics_cost
# of 1.0. Tune against real freight data once available.
MAX_TRANSIT_DAYS = 35
MAX_FREIGHT_COST_USD_PER_KG = 1.20


@dataclass
class LogisticsSignal:
    destination_country: str
    sea_transit_days: int
    freight_cost_usd_per_kg: float
    customs_complexity: float  # 0-1, as provided by the data source
    logistics_cost_score: float  # 0-1, blended and normalized


@dataclass
class LogisticsAgentOutput:
    sector: str
    signals: list[LogisticsSignal] = field(default_factory=list)

    def for_country(self, country: str) -> LogisticsSignal | None:
        country = country.upper()
        for signal in self.signals:
            if signal.destination_country == country:
                return signal
        return None


def _normalize(value: float, cap: float) -> float:
    return round(min(max(value, 0) / cap, 1.0), 2)


def _blended_logistics_cost(
    transit_days: int, freight_cost: float, customs_complexity: float
) -> float:
    """
    Equal-weighted blend of normalized transit time, freight cost, and
    customs complexity. All three already sit on a comparable 0-1
    scale after normalization, so a simple average is a reasonable
    starting point — revisit the weighting once real freight data
    shows which factor actually drives cost/friction the most.
    """
    transit_score = _normalize(transit_days, MAX_TRANSIT_DAYS)
    freight_score = _normalize(freight_cost, MAX_FREIGHT_COST_USD_PER_KG)
    customs_score = min(max(customs_complexity, 0), 1.0)

    blended = (transit_score + freight_score + customs_score) / 3
    return round(blended, 2)


def run_logistics_agent(
    sector: str,
    target_countries: list[str],
) -> LogisticsAgentOutput:
    """
    The Logistics Agent's entry point, called by the orchestrator like
    any other sub-agent. Logistics is modeled per destination country
    (freight lanes don't vary by HS code in this mock data), so the
    scorer looks up by country regardless of which HS code a given
    opportunity score is for.
    """
    signals: list[LogisticsSignal] = []

    for country in target_countries:
        data = get_logistics_data(country)

        signals.append(
            LogisticsSignal(
                destination_country=country.upper(),
                sea_transit_days=data["sea_transit_days"],
                freight_cost_usd_per_kg=data.get("freight_cost_usd_per_kg") or data.get("freight_cost_usd_per_kg_sea", 1.0),
                customs_complexity=data["customs_complexity"],
                logistics_cost_score=_blended_logistics_cost(
                    data["sea_transit_days"],
                    data.get("freight_cost_usd_per_kg") or data.get("freight_cost_usd_per_kg_sea", 1.0),
                    data["customs_complexity"],
                ),
            )
        )

    return LogisticsAgentOutput(sector=sector, signals=signals)
