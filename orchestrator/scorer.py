"""
Opportunity scoring.

    Score = (Demand Growth x Import Gap x Price Premium)
            / (Capability Distance + Competition Density + Logistics Cost)

Status of each factor (all six are now real, as of the Logistics Agent):
    Demand Growth        real  (Demand Signal Agent)
    Competition Density   real  (Demand Signal Agent)
    Import Gap            real, derived from Pricing Agent
    Price Premium          real, derived from Pricing Agent
    Capability Distance   real, derived from Capability Gap Agent
    Logistics Cost         real, derived from Logistics Agent

Every derived factor still falls back to a conservative constant if its
source agent didn't run or had no data for a given pair/country, so
scoring never breaks — it just gets less precise for that one row.
"""

from agents.demand_signal_agent import DemandSignalAgentOutput
from agents.pricing_agent import PricingAgentOutput, PricingSignal
from agents.capability_gap_agent import CapabilityGapAgentOutput
from agents.logistics_agent import LogisticsAgentOutput
from orchestrator.state import OpportunityScore, OrchestratorState

# Used only when the Capability Gap Agent didn't run / failed.
FALLBACK_CAPABILITY_DISTANCE = 0.4

# Used only when the Pricing Agent has no data for a given pair.
FALLBACK_IMPORT_GAP = 0.6
FALLBACK_PRICE_PREMIUM = 1.15

# Used only when the Logistics Agent didn't run / has no data for a country.
FALLBACK_LOGISTICS_COST = 0.3


def _pricing_lookup(
    pricing_output: PricingAgentOutput | None,
) -> dict[tuple[str, str], PricingSignal]:
    if pricing_output is None:
        return {}
    return {
        (p.hs_code, p.destination_country): p for p in pricing_output.pricing
    }


def _derive_import_gap(pricing_signal: PricingSignal | None) -> float:
    """
    Higher (import price / Indian export price) implies a bigger gap
    for Indian exporters to close — i.e. more room to capture share.
    Normalized to 0-1, capped.
    """
    if pricing_signal is None or pricing_signal.average_indian_export_price <= 0:
        return FALLBACK_IMPORT_GAP

    ratio = (
        pricing_signal.average_import_price
        / pricing_signal.average_indian_export_price
    )
    return round(min(ratio / 2, 1.0), 2)


def _derive_price_premium(pricing_signal: PricingSignal | None) -> float:
    """
    Retail price relative to the recommended FOB price — how much
    margin/premium sits between what the exporter charges and what the
    market pays at retail.
    """
    if pricing_signal is None or pricing_signal.recommended_fob_price <= 0:
        return FALLBACK_PRICE_PREMIUM

    return round(
        pricing_signal.estimated_retail_price
        / pricing_signal.recommended_fob_price,
        2,
    )


def _derive_capability_distance(
    capability_output: CapabilityGapAgentOutput | None,
) -> float:
    if capability_output is None:
        return FALLBACK_CAPABILITY_DISTANCE
    return capability_output.capability_distance


def _derive_logistics_cost(
    logistics_output: LogisticsAgentOutput | None, country: str
) -> float:
    if logistics_output is None:
        return FALLBACK_LOGISTICS_COST
    signal = logistics_output.for_country(country)
    if signal is None:
        return FALLBACK_LOGISTICS_COST
    return signal.logistics_cost_score


def compute_scores_node(state: OrchestratorState) -> OrchestratorState:

    demand_output: DemandSignalAgentOutput | None = state.get(
        "demand_signal_output"
    )

    if demand_output is None or not demand_output.signals:
        return {"opportunity_scores": []}

    pricing_output: PricingAgentOutput | None = state.get("pricing_output")
    pricing_by_pair = _pricing_lookup(pricing_output)

    capability_output: CapabilityGapAgentOutput | None = state.get(
        "capability_gap_output"
    )
    capability_distance = _derive_capability_distance(capability_output)

    logistics_output: LogisticsAgentOutput | None = state.get("logistics_output")

    scores: list[OpportunityScore] = []

    for signal in demand_output.signals:

        demand_growth = max(signal.growth_rate_pct / 100, 0.01)
        competition_density = signal.competition_density_score

        pricing_signal = pricing_by_pair.get(
            (signal.hs_code, signal.destination_country)
        )

        import_gap = _derive_import_gap(pricing_signal)
        price_premium = _derive_price_premium(pricing_signal)
        logistics_cost = _derive_logistics_cost(
            logistics_output, signal.destination_country
        )

        numerator = demand_growth * import_gap * price_premium
        denominator = capability_distance + competition_density + logistics_cost
        raw_score = numerator / denominator if denominator > 0 else 0
        score = round(min(raw_score * 60, 100), 1)

        breakdown = {
            "demand_growth_pct": signal.growth_rate_pct,
            "surge_detected": signal.surge_detected,
            "competition_density": competition_density,
            "active_indian_suppliers": signal.active_indian_suppliers,
            "import_gap": import_gap,
            "price_premium": price_premium,
            "capability_distance": capability_distance,
            "logistics_cost": logistics_cost,
        }

        if pricing_signal:
            breakdown["recommended_fob_price"] = pricing_signal.recommended_fob_price
            breakdown["expected_margin_pct"] = pricing_signal.expected_margin_pct
            breakdown["competitiveness_score"] = pricing_signal.competitiveness_score

        if capability_output:
            breakdown["capability_gap_score"] = capability_output.gap_score
            if capability_output.missing_requirements:
                breakdown["missing_requirements"] = capability_output.missing_requirements

        logistics_signal = (
            logistics_output.for_country(signal.destination_country)
            if logistics_output
            else None
        )
        if logistics_signal:
            breakdown["sea_transit_days"] = logistics_signal.sea_transit_days
            breakdown["freight_cost_usd_per_kg"] = logistics_signal.freight_cost_usd_per_kg
            breakdown["customs_complexity"] = logistics_signal.customs_complexity

        real_factors = ["demand", "competition"]
        placeholder_factors = []

        if pricing_signal:
            real_factors.append("pricing (import gap, price premium)")
        else:
            placeholder_factors.append("import gap/price premium (no pricing data for this pair)")

        if capability_output:
            real_factors.append("capability distance")
        else:
            placeholder_factors.append("capability distance")

        if logistics_signal:
            real_factors.append("logistics cost")
        else:
            placeholder_factors.append("logistics cost (no logistics data for this country)")

        note = f"Live/derived data: {', '.join(real_factors)}."
        if placeholder_factors:
            note += f" Still placeholder: {', '.join(placeholder_factors)}."

        scores.append(
            {
                "hs_code": signal.hs_code,
                "destination_country": signal.destination_country,
                "score": score,
                "score_breakdown": breakdown,
                "note": note,
            }
        )

    scores.sort(key=lambda x: x["score"], reverse=True)

    return {"opportunity_scores": scores}
