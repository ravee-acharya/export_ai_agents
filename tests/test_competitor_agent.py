"""
Unit tests for agents/competitor_agent.py.

Uses the agent's own embedded MOCK_DATA (same approach as
test_pricing_agent.py) since the data lives inside the agent module
itself, tested via the public run_competitor_agent() interface.
"""

from agents.competitor_agent import run_competitor_agent


def test_known_pair_returns_competitor_signal():
    output = run_competitor_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["US"]
    )
    assert len(output.signals) == 1
    signal = output.signals[0]
    assert signal.hs_code == "6302"
    assert signal.destination_country == "US"
    assert len(signal.top_competitors) > 0


def test_unknown_hs_code_skipped_not_errored():
    output = run_competitor_agent(
        sector="textiles", hs_codes=["9999"], target_countries=["US"]
    )
    assert output.signals == []


def test_unknown_country_for_known_hs_code_skipped():
    output = run_competitor_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["ZZ"]
    )
    assert output.signals == []


def test_market_concentration_is_sum_of_top_competitor_shares(monkeypatch):
    monkeypatch.setattr(
        "agents.competitor_agent.MOCK_DATA",
        {
            "1234": {
                "US": {
                    "top_competitors": [("China", 40.0, 5.0), ("Vietnam", 20.0, 5.5)],
                    "india_market_share_pct": 10.0,
                    "india_avg_price_usd": 5.0,
                }
            }
        },
    )

    output = run_competitor_agent(
        sector="textiles", hs_codes=["1234"], target_countries=["US"]
    )
    assert output.signals[0].market_concentration == 0.6


def test_market_concentration_capped_at_one(monkeypatch):
    monkeypatch.setattr(
        "agents.competitor_agent.MOCK_DATA",
        {
            "1234": {
                "US": {
                    "top_competitors": [("China", 70.0, 5.0), ("Vietnam", 60.0, 5.0)],
                    "india_market_share_pct": 5.0,
                    "india_avg_price_usd": 5.0,
                }
            }
        },
    )

    output = run_competitor_agent(
        sector="textiles", hs_codes=["1234"], target_countries=["US"]
    )
    assert output.signals[0].market_concentration == 1.0


def test_price_position_cheaper(monkeypatch):
    monkeypatch.setattr(
        "agents.competitor_agent.MOCK_DATA",
        {
            "1234": {
                "US": {
                    "top_competitors": [("China", 40.0, 10.0)],
                    "india_market_share_pct": 5.0,
                    "india_avg_price_usd": 8.0,  # 20% cheaper than 10.0
                }
            }
        },
    )
    output = run_competitor_agent(
        sector="textiles", hs_codes=["1234"], target_countries=["US"]
    )
    assert output.signals[0].price_position == "cheaper"


def test_price_position_more_expensive(monkeypatch):
    monkeypatch.setattr(
        "agents.competitor_agent.MOCK_DATA",
        {
            "1234": {
                "US": {
                    "top_competitors": [("China", 40.0, 10.0)],
                    "india_market_share_pct": 5.0,
                    "india_avg_price_usd": 12.0,  # 20% more expensive
                }
            }
        },
    )
    output = run_competitor_agent(
        sector="textiles", hs_codes=["1234"], target_countries=["US"]
    )
    assert output.signals[0].price_position == "more expensive"


def test_price_position_comparable_within_band(monkeypatch):
    monkeypatch.setattr(
        "agents.competitor_agent.MOCK_DATA",
        {
            "1234": {
                "US": {
                    "top_competitors": [("China", 40.0, 10.0)],
                    "india_market_share_pct": 5.0,
                    "india_avg_price_usd": 10.2,  # within 5% band
                }
            }
        },
    )
    output = run_competitor_agent(
        sector="textiles", hs_codes=["1234"], target_countries=["US"]
    )
    assert output.signals[0].price_position == "comparable"


def test_for_pair_lookup_works():
    output = run_competitor_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["US"]
    )
    signal = output.for_pair("6302", "US")
    assert signal is not None
    assert signal.hs_code == "6302"


def test_for_pair_returns_none_when_absent():
    output = run_competitor_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["US"]
    )
    assert output.for_pair("9999", "ZZ") is None


def test_multiple_hs_codes_and_countries_cross_product():
    output = run_competitor_agent(
        sector="textiles", hs_codes=["6302", "5911"], target_countries=["US", "DE"]
    )
    pairs = {(s.hs_code, s.destination_country) for s in output.signals}
    # 6302 covers both US and DE, 5911 only covers US in MOCK_DATA
    assert pairs == {("6302", "US"), ("6302", "DE"), ("5911", "US")}
