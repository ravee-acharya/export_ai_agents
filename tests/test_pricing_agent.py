"""
Unit tests for agents/pricing_agent.py.

Uses the agent's own embedded MOCK_DATA directly (it's static, unlike
the other agents' external data sources) but tests it via the public
run_pricing_agent() interface rather than reaching into MOCK_DATA, so
these tests keep working if the mock values themselves change.
"""

from agents.pricing_agent import run_pricing_agent


def test_known_pair_returns_pricing_signal():
    output = run_pricing_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["US"]
    )

    assert len(output.pricing) == 1
    signal = output.pricing[0]
    assert signal.hs_code == "6302"
    assert signal.destination_country == "US"
    assert signal.recommended_fob_price > 0


def test_unknown_hs_code_skipped_not_errored():
    output = run_pricing_agent(
        sector="textiles", hs_codes=["9999"], target_countries=["US"]
    )
    assert output.pricing == []


def test_unknown_country_for_known_hs_code_skipped():
    output = run_pricing_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["ZZ"]
    )
    assert output.pricing == []


def test_fob_price_derived_from_indian_export_price():
    output = run_pricing_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["US"]
    )
    signal = output.pricing[0]
    # FOB = indian_price * 1.08 per the agent's own markup logic
    expected_fob = round(signal.average_indian_export_price * 1.08, 2)
    assert signal.recommended_fob_price == expected_fob


def test_margin_percent_is_consistent_with_fob_and_indian_price():
    output = run_pricing_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["US"]
    )
    signal = output.pricing[0]
    expected_margin = round(
        (
            (signal.recommended_fob_price - signal.average_indian_export_price)
            / signal.average_indian_export_price
        )
        * 100,
        1,
    )
    assert signal.expected_margin_pct == expected_margin


def test_competitiveness_score_capped_at_ten():
    output = run_pricing_agent(
        sector="textiles",
        hs_codes=["6302", "5911", "6204"],
        target_countries=["US", "DE", "CA", "AU", "AE"],
    )
    for signal in output.pricing:
        assert 0 <= signal.competitiveness_score <= 10.0


def test_multiple_hs_codes_and_countries_cross_product():
    output = run_pricing_agent(
        sector="textiles",
        hs_codes=["6302", "5911"],
        target_countries=["US", "DE"],
    )
    pairs = {(p.hs_code, p.destination_country) for p in output.pricing}
    assert pairs == {("6302", "US"), ("6302", "DE"), ("5911", "US"), ("5911", "DE")}
