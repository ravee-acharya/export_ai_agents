"""
Unit tests for agents/demand_signal_agent.py.

Monkeypatches fetch_import_data so these tests don't depend on the
actual contents of data_sources/mock_trade_api.py — they verify the
agent's own logic (growth calc, surge detection, competition density
normalization), not the mock data.
"""

import pytest

from agents.demand_signal_agent import (
    SURGE_THRESHOLD_PCT,
    run_demand_signal_agent,
)


def _fake_fetch(monthly_volumes, active_indian_suppliers=5):
    def _fetch(hs_code, destination_country, sector, lookback_months):
        return {
            "hs_code": hs_code,
            "destination_country": destination_country,
            "sector": sector,
            "monthly_volumes": monthly_volumes,
            "active_indian_suppliers": active_indian_suppliers,
            "data_source": "test",
            "as_of": "2026-07-13",
        }
    return _fetch


def test_growth_rate_calculation(monkeypatch):
    # Volume doubles over 5 periods -> ~14.87% average monthly growth
    volumes = [{"volume_usd": v} for v in [100, 110, 120, 140, 160, 200]]
    monkeypatch.setattr(
        "agents.demand_signal_agent.fetch_import_data",
        _fake_fetch(volumes),
    )

    output = run_demand_signal_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["US"]
    )

    assert len(output.signals) == 1
    signal = output.signals[0]
    assert signal.growth_rate_pct == pytest.approx(14.87, abs=0.5)


def test_surge_detection_above_threshold(monkeypatch):
    # Strong growth should trip surge_detected
    volumes = [{"volume_usd": v} for v in [100, 200, 400, 800]]
    monkeypatch.setattr(
        "agents.demand_signal_agent.fetch_import_data",
        _fake_fetch(volumes),
    )

    output = run_demand_signal_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["US"]
    )

    signal = output.signals[0]
    assert signal.growth_rate_pct >= SURGE_THRESHOLD_PCT
    assert signal.surge_detected is True


def test_no_surge_below_threshold(monkeypatch):
    volumes = [{"volume_usd": v} for v in [100, 101, 102, 103]]
    monkeypatch.setattr(
        "agents.demand_signal_agent.fetch_import_data",
        _fake_fetch(volumes),
    )

    output = run_demand_signal_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["US"]
    )

    assert output.signals[0].surge_detected is False


def test_competition_density_normalization(monkeypatch):
    volumes = [{"volume_usd": v} for v in [100, 110]]

    # Above the cap (20) should clamp to 1.0
    monkeypatch.setattr(
        "agents.demand_signal_agent.fetch_import_data",
        _fake_fetch(volumes, active_indian_suppliers=50),
    )
    output = run_demand_signal_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["US"]
    )
    assert output.signals[0].competition_density_score == 1.0


def test_cross_product_of_hs_codes_and_countries(monkeypatch):
    volumes = [{"volume_usd": v} for v in [100, 110]]
    monkeypatch.setattr(
        "agents.demand_signal_agent.fetch_import_data",
        _fake_fetch(volumes),
    )

    output = run_demand_signal_agent(
        sector="textiles",
        hs_codes=["6302", "5911"],
        target_countries=["US", "DE"],
    )

    # 2 HS codes x 2 countries = 4 signals
    assert len(output.signals) == 4
    pairs = {(s.hs_code, s.destination_country) for s in output.signals}
    assert pairs == {("6302", "US"), ("6302", "DE"), ("5911", "US"), ("5911", "DE")}


def test_top_signal_returns_highest_growth(monkeypatch):
    call_count = {"n": 0}

    def _fetch(hs_code, destination_country, sector, lookback_months):
        call_count["n"] += 1
        # First call: flat, second call: strong growth
        if call_count["n"] == 1:
            volumes = [{"volume_usd": v} for v in [100, 100]]
        else:
            volumes = [{"volume_usd": v} for v in [100, 300]]
        return {
            "hs_code": hs_code,
            "destination_country": destination_country,
            "sector": sector,
            "monthly_volumes": volumes,
            "active_indian_suppliers": 5,
            "data_source": "test",
            "as_of": "2026-07-13",
        }

    monkeypatch.setattr("agents.demand_signal_agent.fetch_import_data", _fetch)

    output = run_demand_signal_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["US", "DE"]
    )

    top = output.top_signal()
    assert top is not None
    assert top.growth_rate_pct == max(s.growth_rate_pct for s in output.signals)


def test_empty_signals_top_signal_returns_none():
    from agents.demand_signal_agent import DemandSignalAgentOutput

    output = DemandSignalAgentOutput(sector="textiles", signals=[])
    assert output.top_signal() is None
