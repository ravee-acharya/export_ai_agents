"""
Unit tests for agents/logistics_agent.py.

Monkeypatches get_logistics_data so these tests verify the agent's own
normalization/blending logic, not the specific mock freight numbers.
"""

from agents.logistics_agent import (
    MAX_FREIGHT_COST_USD_PER_KG,
    MAX_TRANSIT_DAYS,
    run_logistics_agent,
)


def _fake_data(transit_days, freight_cost, customs_complexity):
    return lambda country: {
        "sea_transit_days": transit_days,
        "freight_cost_usd_per_kg": freight_cost,
        "customs_complexity": customs_complexity,
    }


def test_logistics_cost_score_within_bounds(monkeypatch):
    monkeypatch.setattr(
        "agents.logistics_agent.get_logistics_data", _fake_data(20, 0.6, 0.4)
    )

    output = run_logistics_agent(sector="textiles", target_countries=["US"])

    signal = output.signals[0]
    assert 0.0 <= signal.logistics_cost_score <= 1.0


def test_maximum_values_produce_near_maximal_cost(monkeypatch):
    monkeypatch.setattr(
        "agents.logistics_agent.get_logistics_data",
        _fake_data(MAX_TRANSIT_DAYS, MAX_FREIGHT_COST_USD_PER_KG, 1.0),
    )

    output = run_logistics_agent(sector="textiles", target_countries=["US"])

    assert output.signals[0].logistics_cost_score == 1.0


def test_minimal_values_produce_near_zero_cost(monkeypatch):
    monkeypatch.setattr(
        "agents.logistics_agent.get_logistics_data", _fake_data(0, 0, 0)
    )

    output = run_logistics_agent(sector="textiles", target_countries=["US"])

    assert output.signals[0].logistics_cost_score < 0.5  # near-zero with fallback freight


def test_values_above_cap_dont_exceed_one(monkeypatch):
    # Transit days double the cap, freight cost triple the cap
    monkeypatch.setattr(
        "agents.logistics_agent.get_logistics_data",
        _fake_data(MAX_TRANSIT_DAYS * 2, MAX_FREIGHT_COST_USD_PER_KG * 3, 1.0),
    )

    output = run_logistics_agent(sector="textiles", target_countries=["US"])

    assert output.signals[0].logistics_cost_score == 1.0


def test_for_country_lookup_is_case_insensitive(monkeypatch):
    monkeypatch.setattr(
        "agents.logistics_agent.get_logistics_data", _fake_data(20, 0.6, 0.4)
    )

    output = run_logistics_agent(sector="textiles", target_countries=["us"])

    assert output.for_country("US") is not None
    assert output.for_country("us") is not None


def test_for_country_returns_none_when_not_present(monkeypatch):
    monkeypatch.setattr(
        "agents.logistics_agent.get_logistics_data", _fake_data(20, 0.6, 0.4)
    )

    output = run_logistics_agent(sector="textiles", target_countries=["US"])

    assert output.for_country("ZZ") is None


def test_multiple_countries_each_get_own_signal(monkeypatch):
    monkeypatch.setattr(
        "agents.logistics_agent.get_logistics_data", _fake_data(20, 0.6, 0.4)
    )

    output = run_logistics_agent(
        sector="textiles", target_countries=["US", "DE", "AE"]
    )

    assert len(output.signals) == 3
    assert {s.destination_country for s in output.signals} == {"US", "DE", "AE"}
