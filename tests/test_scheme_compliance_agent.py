"""
Unit tests for agents/scheme_compliance_agent.py.

Monkeypatches the knowledge-base lookups so these tests verify the
agent's eligibility logic, not the actual scheme/compliance data.
"""

from agents.scheme_compliance_agent import run_scheme_compliance_agent


def _fake_scheme(scheme_id, min_rev=0, max_rev=None, requires_udyam=False):
    return {
        "scheme_id": scheme_id,
        "name": f"Scheme {scheme_id}",
        "issuing_body": "Test Ministry",
        "benefit_summary": "Test benefit",
        "eligibility": {
            "requires_udyam_registration": requires_udyam,
            "min_revenue_cr": min_rev,
            "max_revenue_cr": max_rev,
        },
        "application_notes": "Apply via test portal.",
    }


def test_eligible_when_within_revenue_band(monkeypatch):
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_schemes_for_sector",
        lambda sector: [_fake_scheme("A", min_rev=10, max_rev=100)],
    )
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_compliance_requirements",
        lambda country: [],
    )

    output = run_scheme_compliance_agent(
        sector="textiles",
        target_countries=["US"],
        sme_revenue_cr=40,
        has_udyam_registration=True,
    )

    assert len(output.eligible_schemes()) == 1
    assert output.eligible_schemes()[0].scheme_id == "A"


def test_ineligible_when_revenue_exceeds_cap(monkeypatch):
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_schemes_for_sector",
        lambda sector: [_fake_scheme("A", min_rev=0, max_rev=20)],
    )
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_compliance_requirements",
        lambda country: [],
    )

    output = run_scheme_compliance_agent(
        sector="textiles", target_countries=["US"], sme_revenue_cr=40
    )

    assert len(output.eligible_schemes()) == 0
    assert "exceeds scheme cap" in output.matched_schemes[0].eligibility_notes


def test_ineligible_when_revenue_below_minimum(monkeypatch):
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_schemes_for_sector",
        lambda sector: [_fake_scheme("A", min_rev=50, max_rev=None)],
    )
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_compliance_requirements",
        lambda country: [],
    )

    output = run_scheme_compliance_agent(
        sector="textiles", target_countries=["US"], sme_revenue_cr=10
    )

    assert len(output.eligible_schemes()) == 0
    assert "below scheme minimum" in output.matched_schemes[0].eligibility_notes


def test_ineligible_when_udyam_required_but_missing(monkeypatch):
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_schemes_for_sector",
        lambda sector: [_fake_scheme("A", requires_udyam=True)],
    )
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_compliance_requirements",
        lambda country: [],
    )

    output = run_scheme_compliance_agent(
        sector="textiles",
        target_countries=["US"],
        sme_revenue_cr=40,
        has_udyam_registration=False,
    )

    assert len(output.eligible_schemes()) == 0
    assert "Udyam" in output.matched_schemes[0].eligibility_notes


def test_eligible_schemes_sorted_first(monkeypatch):
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_schemes_for_sector",
        lambda sector: [
            _fake_scheme("INELIGIBLE", min_rev=1000),
            _fake_scheme("ELIGIBLE", min_rev=0, max_rev=None),
        ],
    )
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_compliance_requirements",
        lambda country: [],
    )

    output = run_scheme_compliance_agent(
        sector="textiles", target_countries=["US"], sme_revenue_cr=40
    )

    assert output.matched_schemes[0].scheme_id == "ELIGIBLE"
    assert output.matched_schemes[0].eligible is True


def test_compliance_requirements_populated_per_country(monkeypatch):
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_schemes_for_sector",
        lambda sector: [],
    )
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_compliance_requirements",
        lambda country: [f"requirement-for-{country.upper()}"],
    )

    output = run_scheme_compliance_agent(
        sector="textiles", target_countries=["us", "de"]
    )

    countries = {c.country for c in output.compliance_by_country}
    assert countries == {"US", "DE"}


def test_no_revenue_provided_skips_revenue_checks(monkeypatch):
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_schemes_for_sector",
        lambda sector: [_fake_scheme("A", min_rev=50, max_rev=100)],
    )
    monkeypatch.setattr(
        "agents.scheme_compliance_agent.get_compliance_requirements",
        lambda country: [],
    )

    # sme_revenue_cr=None -> revenue eligibility isn't evaluated at all
    output = run_scheme_compliance_agent(
        sector="textiles", target_countries=["US"], sme_revenue_cr=None
    )

    assert output.matched_schemes[0].eligible is True
