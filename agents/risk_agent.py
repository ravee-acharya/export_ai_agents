"""
Risk Intelligence Agent.

Pattern A from agents/_template_agent.py: deterministic fetch-and-
compute, like Demand Signal, Scheme/Compliance, and Logistics. Country
risk classifications (political stability, currency volatility,
payment default risk, sanctions status) come from structured reference
data — no fuzzy judgment call needed here, unlike Capability Gap.

Unlike Pricing, Capability Gap, and Logistics, this agent's output does
NOT feed the opportunity scoring formula directly — risk is a
different kind of signal than "how good is this opportunity" (an SME
might reasonably still pursue a high-scoring, higher-risk market with
mitigations like ECGC cover or upfront payment terms). Instead, like
Scheme/Compliance, it's surfaced separately: in the dashboard and in
the synthesizer's summary, as a distinct decision input rather than a
multiplier baked into the score.
"""

from dataclasses import dataclass, field

from data_sources.risk_data import get_risk_data

# Overall risk score bands -> human-readable risk level.
_LEVEL_THRESHOLDS = [
    (0.25, "Low"),
    (0.50, "Moderate"),
    (0.75, "High"),
]
_HIGHEST_LEVEL = "Severe"


@dataclass
class RiskSignal:
    destination_country: str
    political_risk_score: float
    currency_volatility_score: float
    payment_default_risk_score: float
    overall_risk_score: float  # 0-1, blended
    risk_level: str  # Low / Moderate / High / Severe
    sanctions_flag: bool
    ecgc_cover_available: bool
    notes: str


@dataclass
class RiskAgentOutput:
    sector: str
    signals: list[RiskSignal] = field(default_factory=list)

    def for_country(self, country: str) -> RiskSignal | None:
        country = country.upper()
        for signal in self.signals:
            if signal.destination_country == country:
                return signal
        return None

    def highest_risk_signal(self) -> RiskSignal | None:
        if not self.signals:
            return None
        return max(self.signals, key=lambda s: s.overall_risk_score)


def _risk_level(overall_score: float) -> str:
    for threshold, level in _LEVEL_THRESHOLDS:
        if overall_score <= threshold:
            return level
    return _HIGHEST_LEVEL


def _blend_overall_risk(
    political_risk: float, currency_volatility: float, payment_default_risk: float
) -> float:
    """
    Equal-weighted blend, consistent with the Logistics Agent's
    approach to combining multiple 0-1 factors. Payment default risk
    is arguably the most consequential for an SME (it directly affects
    cash flow), so this weighting is worth revisiting once real
    default-rate data is available to validate it.
    """
    blended = (political_risk + currency_volatility + payment_default_risk) / 3
    return round(blended, 2)


def run_risk_agent(
    sector: str,
    target_countries: list[str],
) -> RiskAgentOutput:
    """
    The Risk Intelligence Agent's entry point, called by the
    orchestrator like any other sub-agent. Modeled per destination
    country, like Logistics — country risk doesn't vary by HS code in
    this mock data.
    """
    signals: list[RiskSignal] = []

    for country in target_countries:
        data = get_risk_data(country)

        overall = _blend_overall_risk(
            data["political_risk"],
            data["currency_volatility"],
            data["payment_default_risk"],
        )

        signals.append(
            RiskSignal(
                destination_country=country.upper(),
                political_risk_score=data["political_risk"],
                currency_volatility_score=data["currency_volatility"],
                payment_default_risk_score=data["payment_default_risk"],
                overall_risk_score=overall,
                risk_level=_risk_level(overall),
                sanctions_flag=data["sanctions_flag"],
                ecgc_cover_available=data["ecgc_cover_available"],
                notes=data["notes"],
            )
        )

    return RiskAgentOutput(sector=sector, signals=signals)
