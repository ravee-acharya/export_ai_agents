"""
Integration tests for orchestrator/scorer.py — verifies the scoring
formula correctly consumes real agent outputs when present, and falls
back cleanly when an agent's output is missing or has no data for a
given hs_code/country pair. This is the piece most at risk of silent
bugs, since scorer.py blends five different agents' outputs together.
"""

from agents.demand_signal_agent import DemandSignal, DemandSignalAgentOutput
from agents.pricing_agent import PricingAgentOutput, PricingSignal
from agents.capability_gap_agent import CapabilityGapAgentOutput
from agents.logistics_agent import LogisticsAgentOutput, LogisticsSignal
from orchestrator.scorer import (
    FALLBACK_CAPABILITY_DISTANCE,
    FALLBACK_IMPORT_GAP,
    FALLBACK_LOGISTICS_COST,
    FALLBACK_PRICE_PREMIUM,
    compute_scores_node,
)


def _demand_signal(hs_code="6302", country="US", growth=10.0, competition=0.3):
    return DemandSignal(
        hs_code=hs_code,
        destination_country=country,
        sector="textiles",
        growth_rate_pct=growth,
        surge_detected=growth >= 15.0,
        active_indian_suppliers=5,
        competition_density_score=competition,
        latest_monthly_volume_usd=500_000,
        data_source="test",
        as_of="2026-07-13",
    )


def test_no_demand_signals_returns_empty_scores():
    state = {"demand_signal_output": DemandSignalAgentOutput(sector="textiles", signals=[])}
    result = compute_scores_node(state)
    assert result["opportunity_scores"] == []


def test_missing_demand_output_returns_empty_scores():
    result = compute_scores_node({})
    assert result["opportunity_scores"] == []


def test_all_fallbacks_used_when_no_other_agents_ran():
    demand_output = DemandSignalAgentOutput(sector="textiles", signals=[_demand_signal()])
    state = {"demand_signal_output": demand_output}

    result = compute_scores_node(state)

    score = result["opportunity_scores"][0]
    b = score["score_breakdown"]
    assert b["import_gap"] == FALLBACK_IMPORT_GAP
    assert b["price_premium"] == FALLBACK_PRICE_PREMIUM
    assert b["capability_distance"] == FALLBACK_CAPABILITY_DISTANCE
    assert b["logistics_cost"] == FALLBACK_LOGISTICS_COST
    assert "recommended_fob_price" not in b
    assert "capability_gap_score" not in b


def test_pricing_data_used_when_pair_matches():
    demand_output = DemandSignalAgentOutput(sector="textiles", signals=[_demand_signal()])
    pricing_output = PricingAgentOutput(
        pricing=[
            PricingSignal(
                hs_code="6302",
                destination_country="US",
                average_import_price=8.60,
                average_indian_export_price=6.10,
                estimated_retail_price=22.40,
                recommended_fob_price=6.59,
                expected_margin_pct=8.0,
                competitiveness_score=10.0,
            )
        ]
    )
    state = {"demand_signal_output": demand_output, "pricing_output": pricing_output}

    result = compute_scores_node(state)
    b = result["opportunity_scores"][0]["score_breakdown"]

    assert b["import_gap"] != FALLBACK_IMPORT_GAP
    assert b["price_premium"] != FALLBACK_PRICE_PREMIUM
    assert b["recommended_fob_price"] == 6.59


def test_pricing_fallback_when_pair_not_in_pricing_output():
    # Demand signal is for HS 9999, but pricing only covers HS 6302 --
    # this pair should fall back rather than crash or mismatch.
    demand_output = DemandSignalAgentOutput(
        sector="textiles", signals=[_demand_signal(hs_code="9999")]
    )
    pricing_output = PricingAgentOutput(
        pricing=[
            PricingSignal(
                hs_code="6302",
                destination_country="US",
                average_import_price=8.60,
                average_indian_export_price=6.10,
                estimated_retail_price=22.40,
                recommended_fob_price=6.59,
                expected_margin_pct=8.0,
                competitiveness_score=10.0,
            )
        ]
    )
    state = {"demand_signal_output": demand_output, "pricing_output": pricing_output}

    result = compute_scores_node(state)
    b = result["opportunity_scores"][0]["score_breakdown"]

    assert b["import_gap"] == FALLBACK_IMPORT_GAP
    assert b["price_premium"] == FALLBACK_PRICE_PREMIUM
    assert "Still placeholder" in result["opportunity_scores"][0]["note"]


def test_capability_gap_output_used_when_present():
    demand_output = DemandSignalAgentOutput(sector="textiles", signals=[_demand_signal()])
    capability_output = CapabilityGapAgentOutput(
        sector="textiles",
        target_countries=["US"],
        gap_score=2,
        capability_distance=0.25,
        missing_requirements=["OEKO-TEX"],
        upgrade_path=["Get certified"],
        reasoning="test",
    )
    state = {
        "demand_signal_output": demand_output,
        "capability_gap_output": capability_output,
    }

    result = compute_scores_node(state)
    b = result["opportunity_scores"][0]["score_breakdown"]

    assert b["capability_distance"] == 0.25
    assert b["capability_gap_score"] == 2
    assert b["missing_requirements"] == ["OEKO-TEX"]


def test_logistics_output_used_when_country_matches():
    demand_output = DemandSignalAgentOutput(sector="textiles", signals=[_demand_signal(country="US")])
    logistics_output = LogisticsAgentOutput(
        sector="textiles",
        signals=[
            LogisticsSignal(
                destination_country="US",
                sea_transit_days=28,
                freight_cost_usd_per_kg=0.85,
                customs_complexity=0.5,
                logistics_cost_score=0.55,
            )
        ],
    )
    state = {"demand_signal_output": demand_output, "logistics_output": logistics_output}

    result = compute_scores_node(state)
    b = result["opportunity_scores"][0]["score_breakdown"]

    assert b["logistics_cost"] == 0.55
    assert b["sea_transit_days"] == 28


def test_logistics_fallback_when_country_not_covered():
    demand_output = DemandSignalAgentOutput(sector="textiles", signals=[_demand_signal(country="ZZ")])
    logistics_output = LogisticsAgentOutput(
        sector="textiles",
        signals=[
            LogisticsSignal(
                destination_country="US",
                sea_transit_days=28,
                freight_cost_usd_per_kg=0.85,
                customs_complexity=0.5,
                logistics_cost_score=0.55,
            )
        ],
    )
    state = {"demand_signal_output": demand_output, "logistics_output": logistics_output}

    result = compute_scores_node(state)
    b = result["opportunity_scores"][0]["score_breakdown"]

    assert b["logistics_cost"] == FALLBACK_LOGISTICS_COST


def test_scores_sorted_descending():
    demand_output = DemandSignalAgentOutput(
        sector="textiles",
        signals=[
            _demand_signal(hs_code="A", growth=5.0, competition=0.8),
            _demand_signal(hs_code="B", growth=25.0, competition=0.1),
        ],
    )
    state = {"demand_signal_output": demand_output}

    result = compute_scores_node(state)
    scores = [s["score"] for s in result["opportunity_scores"]]

    assert scores == sorted(scores, reverse=True)


def test_score_is_never_negative_or_absurdly_large():
    demand_output = DemandSignalAgentOutput(sector="textiles", signals=[_demand_signal(growth=50.0)])
    state = {"demand_signal_output": demand_output}

    result = compute_scores_node(state)
    score = result["opportunity_scores"][0]["score"]

    assert 0 <= score <= 100
