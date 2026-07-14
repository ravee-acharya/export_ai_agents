"""
Competitor Agent.

Pattern A from agents/_template_agent.py: deterministic lookup and
computation, like Pricing, Logistics, and Risk. Which countries
dominate a given (hs_code, destination_country) import market, at what
price and market share, is reference data — not a judgment call.

This is a different lens on "competition" than the Demand Signal
Agent's competition_density_score, which measures how many Indian
suppliers are already active. This agent instead answers "who is India
actually competing against globally in this market, and how does
India's pricing/share compare to them" — the international competitive
landscape, not domestic crowding.

Like Risk and Scheme/Compliance, this agent's output does NOT feed the
opportunity scoring formula. Knowing that Vietnam holds 40% share at a
lower price is a strategic input for an SME's decision (e.g. compete on
quality/niche positioning vs. price), not a straightforward penalty —
so it's surfaced separately in the summary/dashboard rather than baked
into the score.
"""

from dataclasses import dataclass, field

# Mock competitor landscape data, mirroring pricing_agent.py's approach
# of embedding static reference data directly in the agent module,
# since it's the same kind of (hs_code, country) -> market data lookup.
#
# Each entry: top_competitors is a list of (country, market_share_pct,
# avg_price_usd) tuples for the largest exporters to that market,
# alongside India's own current share and average price for comparison.
MOCK_DATA = {
    "6302": {
        "US": {
            "top_competitors": [
                ("China", 32.0, 7.10),
                ("Pakistan", 18.0, 6.40),
                ("Vietnam", 12.0, 7.30),
            ],
            "india_market_share_pct": 14.0,
            "india_avg_price_usd": 6.10,
        },
        "DE": {
            "top_competitors": [
                ("China", 28.0, 6.90),
                ("Turkey", 20.0, 7.60),
                ("Pakistan", 15.0, 6.20),
            ],
            "india_market_share_pct": 11.0,
            "india_avg_price_usd": 6.00,
        },
    },
    "5911": {
        "US": {
            "top_competitors": [
                ("China", 45.0, 15.80),
                ("South Korea", 15.0, 17.20),
            ],
            "india_market_share_pct": 8.0,
            "india_avg_price_usd": 14.20,
        },
    },
}


@dataclass
class CompetitorInfo:
    country: str
    market_share_pct: float
    avg_price_usd: float


@dataclass
class CompetitorSignal:
    hs_code: str
    destination_country: str
    top_competitors: list[CompetitorInfo]
    india_market_share_pct: float
    india_avg_price_usd: float
    price_position: str  # "cheaper", "comparable", or "more expensive"
    market_concentration: float  # 0-1, combined share held by top competitors


@dataclass
class CompetitorAgentOutput:
    signals: list[CompetitorSignal] = field(default_factory=list)

    def for_pair(self, hs_code: str, country: str) -> CompetitorSignal | None:
        for signal in self.signals:
            if signal.hs_code == hs_code and signal.destination_country == country.upper():
                return signal
        return None


# A price within this fraction of the competitor average counts as
# "comparable" rather than clearly cheaper/more expensive.
_COMPARABLE_BAND = 0.05


def _price_position(india_price: float, competitor_avg_price: float) -> str:
    if competitor_avg_price <= 0:
        return "comparable"

    diff_ratio = (india_price - competitor_avg_price) / competitor_avg_price

    if diff_ratio < -_COMPARABLE_BAND:
        return "cheaper"
    if diff_ratio > _COMPARABLE_BAND:
        return "more expensive"
    return "comparable"


def run_competitor_agent(
    sector: str,
    hs_codes: list[str],
    target_countries: list[str],
) -> CompetitorAgentOutput:
    """
    The Competitor Agent's entry point, called by the orchestrator like
    any other sub-agent. Silently skips (hs_code, country) pairs not
    covered by MOCK_DATA, matching pricing_agent's behavior, so an
    unmapped pair simply produces no competitor signal rather than an
    error.
    """
    signals: list[CompetitorSignal] = []

    for hs_code in hs_codes:
        if hs_code not in MOCK_DATA:
            continue

        for country in target_countries:
            country_data = MOCK_DATA[hs_code].get(country.upper())
            if country_data is None:
                continue

            top_competitors = [
                CompetitorInfo(country=c, market_share_pct=share, avg_price_usd=price)
                for c, share, price in country_data["top_competitors"]
            ]

            competitor_avg_price = (
                sum(c.avg_price_usd for c in top_competitors) / len(top_competitors)
                if top_competitors
                else 0.0
            )

            market_concentration = round(
                min(sum(c.market_share_pct for c in top_competitors) / 100, 1.0), 2
            )

            signals.append(
                CompetitorSignal(
                    hs_code=hs_code,
                    destination_country=country.upper(),
                    top_competitors=top_competitors,
                    india_market_share_pct=country_data["india_market_share_pct"],
                    india_avg_price_usd=country_data["india_avg_price_usd"],
                    price_position=_price_position(
                        country_data["india_avg_price_usd"], competitor_avg_price
                    ),
                    market_concentration=market_concentration,
                )
            )

    return CompetitorAgentOutput(signals=signals)
