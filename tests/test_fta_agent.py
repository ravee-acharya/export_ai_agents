"""
Unit tests for agents/fta_agent.py.

Monkeypatches get_fta_info so these tests verify the agent's own
eligibility/savings calculation logic, not the specific mock tariff
numbers.
"""

from agents.fta_agent import run_fta_agent


def _fake_info(
    fta_name,
    mfn,
    preferential,
    rules_of_origin="test ROO",
    anti_dumping=0.0,
    countervailing=0.0,
    special_notes=None,
):
    return lambda hs_code, country: {
        "fta_name": fta_name,
        "mfn_tariff_pct": mfn,
        "preferential_tariff_pct": preferential,
        "rules_of_origin": rules_of_origin,
        "anti_dumping_duty_pct": anti_dumping,
        "countervailing_duty_pct": countervailing,
        "special_duty_notes": special_notes,
    }


def test_eligible_pair_computes_correct_savings(monkeypatch):
    monkeypatch.setattr(
        "agents.fta_agent.get_fta_info",
        _fake_info("Test FTA", mfn=10.0, preferential=2.0),
    )

    output = run_fta_agent(sector="textiles", hs_codes=["6302"], target_countries=["AE"])
    signal = output.signals[0]

    assert signal.eligible is True
    assert signal.fta_name == "Test FTA"
    assert signal.tariff_savings_pct == 8.0


def test_ineligible_pair_has_zero_savings(monkeypatch):
    monkeypatch.setattr(
        "agents.fta_agent.get_fta_info",
        _fake_info(None, mfn=10.0, preferential=None),
    )

    output = run_fta_agent(sector="textiles", hs_codes=["6302"], target_countries=["US"])
    signal = output.signals[0]

    assert signal.eligible is False
    assert signal.tariff_savings_pct == 0.0
    assert signal.fta_name is None
    assert signal.preferential_tariff_pct is None


def test_every_pair_produces_a_signal_even_when_ineligible(monkeypatch):
    # Unlike Pricing/Competitor, FTA never silently skips a pair --
    # "no FTA available" is itself a meaningful, always-answerable result.
    monkeypatch.setattr(
        "agents.fta_agent.get_fta_info",
        _fake_info(None, mfn=10.0, preferential=None),
    )

    output = run_fta_agent(
        sector="textiles", hs_codes=["9999"], target_countries=["ZZ"]
    )

    assert len(output.signals) == 1
    assert output.signals[0].eligible is False


def test_eligible_signals_filters_correctly(monkeypatch):
    call_count = {"n": 0}

    def _fetch(hs_code, country):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {
                "fta_name": "Test FTA",
                "mfn_tariff_pct": 10.0,
                "preferential_tariff_pct": 2.0,
                "rules_of_origin": "test",
            }
        return {
            "fta_name": None,
            "mfn_tariff_pct": 10.0,
            "preferential_tariff_pct": None,
            "rules_of_origin": None,
        }

    monkeypatch.setattr("agents.fta_agent.get_fta_info", _fetch)

    output = run_fta_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["AE", "US"]
    )

    eligible = output.eligible_signals()
    assert len(eligible) == 1
    assert eligible[0].destination_country == "AE"


def test_for_pair_lookup_works(monkeypatch):
    monkeypatch.setattr(
        "agents.fta_agent.get_fta_info",
        _fake_info("Test FTA", mfn=10.0, preferential=2.0),
    )

    output = run_fta_agent(sector="textiles", hs_codes=["6302"], target_countries=["AE"])
    signal = output.for_pair("6302", "AE")

    assert signal is not None
    assert signal.hs_code == "6302"


def test_for_pair_returns_none_when_absent(monkeypatch):
    monkeypatch.setattr(
        "agents.fta_agent.get_fta_info",
        _fake_info("Test FTA", mfn=10.0, preferential=2.0),
    )

    output = run_fta_agent(sector="textiles", hs_codes=["6302"], target_countries=["AE"])
    assert output.for_pair("9999", "ZZ") is None


def test_multiple_hs_codes_and_countries_cross_product(monkeypatch):
    monkeypatch.setattr(
        "agents.fta_agent.get_fta_info",
        _fake_info("Test FTA", mfn=10.0, preferential=2.0),
    )

    output = run_fta_agent(
        sector="textiles", hs_codes=["6302", "5911"], target_countries=["AE", "US"]
    )

    pairs = {(s.hs_code, s.destination_country) for s in output.signals}
    assert pairs == {("6302", "AE"), ("6302", "US"), ("5911", "AE"), ("5911", "US")}


def test_effective_tariff_equals_preferential_when_eligible_and_no_special_duties(monkeypatch):
    monkeypatch.setattr(
        "agents.fta_agent.get_fta_info",
        _fake_info("Test FTA", mfn=10.0, preferential=2.0),
    )
    output = run_fta_agent(sector="textiles", hs_codes=["6302"], target_countries=["AE"])
    signal = output.signals[0]

    assert signal.effective_tariff_pct == 2.0
    assert signal.has_special_duties is False


def test_effective_tariff_equals_mfn_when_ineligible_and_no_special_duties(monkeypatch):
    monkeypatch.setattr(
        "agents.fta_agent.get_fta_info",
        _fake_info(None, mfn=10.0, preferential=None),
    )
    output = run_fta_agent(sector="textiles", hs_codes=["6302"], target_countries=["US"])
    signal = output.signals[0]

    assert signal.effective_tariff_pct == 10.0


def test_special_duties_add_on_top_of_preferential_rate(monkeypatch):
    monkeypatch.setattr(
        "agents.fta_agent.get_fta_info",
        _fake_info(
            "Test FTA", mfn=10.0, preferential=2.0,
            anti_dumping=6.5, countervailing=1.0,
        ),
    )
    output = run_fta_agent(sector="textiles", hs_codes=["6302"], target_countries=["AE"])
    signal = output.signals[0]

    # Preferential 2.0 + anti-dumping 6.5 + countervailing 1.0
    assert signal.effective_tariff_pct == 9.5
    assert signal.has_special_duties is True


def test_special_duties_add_on_top_of_mfn_rate_when_ineligible(monkeypatch):
    monkeypatch.setattr(
        "agents.fta_agent.get_fta_info",
        _fake_info(
            None, mfn=10.0, preferential=None,
            anti_dumping=6.5, countervailing=0.0,
        ),
    )
    output = run_fta_agent(sector="textiles", hs_codes=["5911"], target_countries=["US"])
    signal = output.signals[0]

    assert signal.effective_tariff_pct == 16.5
    assert signal.has_special_duties is True


def test_has_special_duties_false_when_both_zero(monkeypatch):
    monkeypatch.setattr(
        "agents.fta_agent.get_fta_info",
        _fake_info("Test FTA", mfn=10.0, preferential=2.0, anti_dumping=0.0, countervailing=0.0),
    )
    output = run_fta_agent(sector="textiles", hs_codes=["6302"], target_countries=["AE"])
    assert output.signals[0].has_special_duties is False


def test_signals_with_special_duties_filters_correctly(monkeypatch):
    call_count = {"n": 0}

    def _fetch(hs_code, country):
        call_count["n"] += 1
        anti_dumping = 6.5 if call_count["n"] == 1 else 0.0
        return {
            "fta_name": None,
            "mfn_tariff_pct": 10.0,
            "preferential_tariff_pct": None,
            "rules_of_origin": None,
            "anti_dumping_duty_pct": anti_dumping,
            "countervailing_duty_pct": 0.0,
            "special_duty_notes": "test" if anti_dumping else None,
        }

    monkeypatch.setattr("agents.fta_agent.get_fta_info", _fetch)

    output = run_fta_agent(
        sector="textiles", hs_codes=["6302"], target_countries=["US", "DE"]
    )

    flagged = output.signals_with_special_duties()
    assert len(flagged) == 1
    assert flagged[0].destination_country == "US"
