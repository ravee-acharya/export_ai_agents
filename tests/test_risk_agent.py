"""
Unit tests for agents/risk_agent.py.

Monkeypatches get_risk_data so these tests verify the agent's own
blending/level-classification logic, not the specific mock risk
numbers.
"""

from agents.risk_agent import run_risk_agent


def _fake_data(political, currency, payment_default, sanctions=False, ecgc=True):
    return lambda country: {
        "political_risk": political,
        "currency_volatility": currency,
        "payment_default_risk": payment_default,
        "sanctions_flag": sanctions,
        "ecgc_cover_available": ecgc,
        "notes": "test note",
    }


def test_overall_risk_score_is_average_of_three_factors(monkeypatch):
    monkeypatch.setattr(
        "agents.risk_agent.get_risk_data", _fake_data(0.3, 0.6, 0.9)
    )

    output = run_risk_agent(sector="textiles", target_countries=["US"])
    signal = output.signals[0]

    assert signal.overall_risk_score == round((0.3 + 0.6 + 0.9) / 3, 2)


def test_risk_level_low_for_low_score(monkeypatch):
    monkeypatch.setattr(
        "agents.risk_agent.get_risk_data", _fake_data(0.1, 0.1, 0.1)
    )
    output = run_risk_agent(sector="textiles", target_countries=["US"])
    assert output.signals[0].risk_level == "Low"


def test_risk_level_moderate_for_mid_score(monkeypatch):
    monkeypatch.setattr(
        "agents.risk_agent.get_risk_data", _fake_data(0.4, 0.4, 0.4)
    )
    output = run_risk_agent(sector="textiles", target_countries=["US"])
    assert output.signals[0].risk_level == "Moderate"


def test_risk_level_high_for_high_score(monkeypatch):
    monkeypatch.setattr(
        "agents.risk_agent.get_risk_data", _fake_data(0.7, 0.7, 0.7)
    )
    output = run_risk_agent(sector="textiles", target_countries=["US"])
    assert output.signals[0].risk_level == "High"


def test_risk_level_severe_for_very_high_score(monkeypatch):
    monkeypatch.setattr(
        "agents.risk_agent.get_risk_data", _fake_data(0.9, 0.9, 0.9)
    )
    output = run_risk_agent(sector="textiles", target_countries=["US"])
    assert output.signals[0].risk_level == "Severe"


def test_sanctions_flag_propagated(monkeypatch):
    monkeypatch.setattr(
        "agents.risk_agent.get_risk_data",
        _fake_data(0.5, 0.5, 0.5, sanctions=True),
    )
    output = run_risk_agent(sector="textiles", target_countries=["US"])
    assert output.signals[0].sanctions_flag is True


def test_ecgc_cover_flag_propagated(monkeypatch):
    monkeypatch.setattr(
        "agents.risk_agent.get_risk_data",
        _fake_data(0.5, 0.5, 0.5, ecgc=False),
    )
    output = run_risk_agent(sector="textiles", target_countries=["US"])
    assert output.signals[0].ecgc_cover_available is False


def test_for_country_lookup_case_insensitive(monkeypatch):
    monkeypatch.setattr(
        "agents.risk_agent.get_risk_data", _fake_data(0.3, 0.3, 0.3)
    )
    output = run_risk_agent(sector="textiles", target_countries=["us"])
    assert output.for_country("US") is not None
    assert output.for_country("us") is not None


def test_for_country_returns_none_when_absent(monkeypatch):
    monkeypatch.setattr(
        "agents.risk_agent.get_risk_data", _fake_data(0.3, 0.3, 0.3)
    )
    output = run_risk_agent(sector="textiles", target_countries=["US"])
    assert output.for_country("ZZ") is None


def test_highest_risk_signal_returns_max(monkeypatch):
    call_count = {"n": 0}

    def _fetch(country):
        call_count["n"] += 1
        score = 0.2 if call_count["n"] == 1 else 0.8
        return {
            "political_risk": score,
            "currency_volatility": score,
            "payment_default_risk": score,
            "sanctions_flag": False,
            "ecgc_cover_available": True,
            "notes": "test",
        }

    monkeypatch.setattr("agents.risk_agent.get_risk_data", _fetch)

    output = run_risk_agent(sector="textiles", target_countries=["US", "DE"])
    highest = output.highest_risk_signal()

    assert highest is not None
    assert highest.overall_risk_score == max(
        s.overall_risk_score for s in output.signals
    )


def test_highest_risk_signal_none_when_no_signals():
    from agents.risk_agent import RiskAgentOutput

    output = RiskAgentOutput(sector="textiles", signals=[])
    assert output.highest_risk_signal() is None


def test_multiple_countries_each_get_own_signal(monkeypatch):
    monkeypatch.setattr(
        "agents.risk_agent.get_risk_data", _fake_data(0.3, 0.3, 0.3)
    )
    output = run_risk_agent(
        sector="textiles", target_countries=["US", "DE", "AE"]
    )
    assert len(output.signals) == 3
    assert {s.destination_country for s in output.signals} == {"US", "DE", "AE"}
