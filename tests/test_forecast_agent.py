"""
Tests for agents/forecast_agent.py — predictive demand forecasting.

Covers the core algorithm (linear regression, projections, confidence
intervals), edge cases (single data point, flat trend, declining trend),
and the agent orchestration entry point.
"""

import pytest
import numpy as np
from agents.forecast_agent import (
    ForecastAgentOutput,
    ForecastSignal,
    MonthlyProjection,
    _confidence_label,
    _fit_linear,
    _outlook_label,
    _project_months,
    run_forecast_agent,
)


# ------------------------------------------------------------------
# _fit_linear
# ------------------------------------------------------------------

def test_fit_linear_perfect_trend():
    data = [
        {"year": "2022", "value_usd": 1_000_000},
        {"year": "2023", "value_usd": 1_200_000},
        {"year": "2024", "value_usd": 1_400_000},
    ]
    slope, base, r2 = _fit_linear(data)
    assert slope == pytest.approx(200_000, rel=0.01)
    assert r2 == pytest.approx(1.0, abs=0.001)


def test_fit_linear_noisy_trend():
    data = [
        {"year": "2022", "value_usd": 1_000_000},
        {"year": "2023", "value_usd": 1_300_000},  # slightly off-trend
        {"year": "2024", "value_usd": 1_400_000},
    ]
    slope, base, r2 = _fit_linear(data)
    assert 0 < r2 < 1.0   # imperfect but positive trend
    assert slope > 0


def test_fit_linear_declining_trend():
    data = [
        {"year": "2022", "value_usd": 2_000_000},
        {"year": "2023", "value_usd": 1_500_000},
        {"year": "2024", "value_usd": 1_000_000},
    ]
    slope, base, r2 = _fit_linear(data)
    assert slope < 0       # declining
    assert r2 == pytest.approx(1.0, abs=0.001)


def test_fit_linear_single_point_returns_zero_slope():
    data = [{"year": "2024", "value_usd": 1_000_000}]
    slope, base, r2 = _fit_linear(data)
    assert slope == 0.0
    assert r2 == 0.0


def test_fit_linear_flat_trend():
    data = [
        {"year": "2022", "value_usd": 1_000_000},
        {"year": "2023", "value_usd": 1_000_000},
        {"year": "2024", "value_usd": 1_000_000},
    ]
    slope, base, r2 = _fit_linear(data)
    assert abs(slope) < 1   # effectively zero
    # R² is undefined for a flat line (ss_tot=0), should return 1.0
    assert r2 == pytest.approx(1.0, abs=0.001)


# ------------------------------------------------------------------
# _confidence_label
# ------------------------------------------------------------------

def test_confidence_high():
    assert _confidence_label(0.90) == "High"
    assert _confidence_label(1.00) == "High"


def test_confidence_moderate():
    assert _confidence_label(0.70) == "Moderate"
    assert _confidence_label(0.50) == "Moderate"


def test_confidence_low():
    assert _confidence_label(0.49) == "Low"
    assert _confidence_label(0.00) == "Low"


# ------------------------------------------------------------------
# _project_months
# ------------------------------------------------------------------

def test_project_months_returns_12():
    projections, growth = _project_months(
        slope_usd_per_year=100_000,
        base_annual_usd=1_000_000,
        base_year=2024,
        r2=1.0,
        n_months=12,
    )
    assert len(projections) == 12


def test_project_months_positive_growth():
    projections, growth = _project_months(
        slope_usd_per_year=150_000,    # 15% annual growth on $1M base
        base_annual_usd=1_000_000,
        base_year=2024,
        r2=1.0,
    )
    assert growth == pytest.approx(15.0, rel=0.05)
    # Each month should be larger than the previous
    values = [p.projected_value_usd for p in projections]
    assert values == sorted(values)


def test_project_months_confidence_intervals_widen_over_time():
    projections, _ = _project_months(
        slope_usd_per_year=100_000,
        base_annual_usd=1_000_000,
        base_year=2024,
        r2=0.6,   # moderate confidence -> wider intervals
    )
    widths = [p.upper_bound_usd - p.lower_bound_usd for p in projections]
    # CI must widen (or stay same) over time — never narrow
    for i in range(1, len(widths)):
        assert widths[i] >= widths[i-1] - 1  # allow tiny float rounding


def test_project_months_no_negative_lower_bound():
    projections, _ = _project_months(
        slope_usd_per_year=-900_000,  # severe decline
        base_annual_usd=1_000_000,
        base_year=2024,
        r2=0.3,
    )
    for p in projections:
        assert p.lower_bound_usd >= 0.0
        assert p.projected_value_usd >= 0.0


def test_project_months_correct_year():
    projections, _ = _project_months(100_000, 1_000_000, 2024, 1.0)
    assert projections[0].month.startswith("2025")
    assert projections[11].month.startswith("2025")


# ------------------------------------------------------------------
# _outlook_label
# ------------------------------------------------------------------

def test_outlook_label_strong_growth():
    label = _outlook_label(18.5, "High", "US")
    assert "strongly growing" in label
    assert "US" in label
    assert "18.5%" in label


def test_outlook_label_moderate_growth():
    label = _outlook_label(7.0, "Moderate", "DE")
    assert "steadily growing" in label
    assert "moderate confidence" in label


def test_outlook_label_decline():
    label = _outlook_label(-12.0, "Low", "BR")
    assert "contracting" in label
    assert "low confidence" in label


# ------------------------------------------------------------------
# run_forecast_agent (integration)
# ------------------------------------------------------------------

def test_run_forecast_agent_returns_one_signal_per_pair():
    from unittest.mock import patch

    fake_data = {
        "hs_code": "6302",
        "destination_country": "US",
        "sector": "textiles",
        "annual_volumes": [
            {"year": "2022", "value_usd": 80_000_000},
            {"year": "2023", "value_usd": 90_000_000},
            {"year": "2024", "value_usd": 102_000_000},
        ],
        "monthly_volumes": [],
        "active_indian_suppliers": 6,
        "data_source": "UN Comtrade API (real data)",
        "as_of": "2026-07-21",
    }

    with patch("data_sources.comtrade_api.fetch_import_data", return_value=fake_data):
        output = run_forecast_agent("textiles", ["6302"], ["US", "DE"])

    assert len(output.signals) == 2
    assert output.sector == "textiles"


def test_run_forecast_agent_uses_pre_fetched_data():
    """Pre-fetched data must be used without calling fetch_import_data again."""
    from unittest.mock import patch, MagicMock

    fake_data = {
        "hs_code": "6302", "destination_country": "US", "sector": "textiles",
        "annual_volumes": [
            {"year": "2022", "value_usd": 80_000_000},
            {"year": "2023", "value_usd": 90_000_000},
            {"year": "2024", "value_usd": 100_000_000},
        ],
        "monthly_volumes": [], "active_indian_suppliers": 6,
        "data_source": "test", "as_of": "2026-07-21",
    }
    pre_fetched = {("6302", "US"): fake_data}

    mock_fetch = MagicMock()
    with patch("data_sources.comtrade_api.fetch_import_data", mock_fetch):
        output = run_forecast_agent(
            "textiles", ["6302"], ["US"],
            trade_data_by_pair=pre_fetched,
        )

    mock_fetch.assert_not_called()
    assert len(output.signals) == 1


def test_run_forecast_agent_signal_fields():
    from unittest.mock import patch

    fake_data = {
        "hs_code": "6302", "destination_country": "US", "sector": "textiles",
        "annual_volumes": [
            {"year": "2022", "value_usd": 80_000_000},
            {"year": "2023", "value_usd": 92_000_000},
            {"year": "2024", "value_usd": 105_000_000},
        ],
        "monthly_volumes": [], "active_indian_suppliers": 6,
        "data_source": "test", "as_of": "2026-07-21",
    }

    with patch("data_sources.comtrade_api.fetch_import_data", return_value=fake_data):
        output = run_forecast_agent("textiles", ["6302"], ["US"])

    signal = output.signals[0]
    assert signal.hs_code == "6302"
    assert signal.destination_country == "US"
    assert len(signal.monthly_projections) == 12
    assert signal.projected_annual_growth_pct > 0   # growing trend
    assert 0.0 <= signal.r_squared <= 1.0
    assert signal.confidence in ("High", "Moderate", "Low")
    assert len(signal.outlook_label) > 0


def test_run_forecast_agent_fallback_when_no_annual_data():
    """Missing annual_volumes must not crash — use latest_annual_value_usd."""
    from unittest.mock import patch

    fake_data = {
        "hs_code": "6302", "destination_country": "US", "sector": "textiles",
        "annual_volumes": [],   # empty — real-world when API returns no data
        "latest_annual_value_usd": 50_000_000,
        "monthly_volumes": [{"month": "2025-01", "volume_usd": 4_000_000}],
        "active_indian_suppliers": 5,
        "data_source": "mock_fallback", "as_of": "2026-07-21",
    }

    with patch("data_sources.comtrade_api.fetch_import_data", return_value=fake_data):
        output = run_forecast_agent("textiles", ["6302"], ["US"])

    assert len(output.signals) == 1
    assert len(output.signals[0].monthly_projections) == 12


def test_forecast_agent_output_best_signal():
    from unittest.mock import patch

    def make_data(country, base):
        return {
            "hs_code": "6302", "destination_country": country, "sector": "textiles",
            "annual_volumes": [
                {"year": "2022", "value_usd": base},
                {"year": "2023", "value_usd": base * 1.1},
                {"year": "2024", "value_usd": base * 1.2},
            ],
            "monthly_volumes": [], "active_indian_suppliers": 5,
            "data_source": "test", "as_of": "2026-07-21",
        }

    call_count = [0]
    countries = ["US", "DE", "AE"]
    bases = [100_000_000, 50_000_000, 80_000_000]

    def fake_fetch(hs_code, destination_country, sector, **kwargs):
        i = countries.index(destination_country)
        return make_data(destination_country, bases[i])

    with patch("data_sources.comtrade_api.fetch_import_data", side_effect=fake_fetch):
        output = run_forecast_agent("textiles", ["6302"], countries)

    best = output.best_signal()
    assert best is not None
    # All have same growth rate (20% each), best_signal picks any one
    assert best.projected_annual_growth_pct > 0
