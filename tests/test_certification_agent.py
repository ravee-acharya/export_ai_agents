"""
Unit tests for agents/certification_agent.py.

Monkeypatches both underlying data sources so these tests verify the
agent's own aggregation/dedup logic, not the specific mock content.
"""

from agents.certification_agent import run_certification_agent


def test_certifications_deduped_across_countries(monkeypatch):
    monkeypatch.setattr(
        "agents.certification_agent.get_capability_requirements",
        lambda sector, country: ["ISO 9001", "OEKO-TEX Standard 100"],
    )
    monkeypatch.setattr(
        "agents.certification_agent.get_certification_details",
        lambda name: {
            "issuing_body": "Test body",
            "typical_cost_usd": (100, 200),
            "typical_timeline_weeks": (1, 2),
            "validity_years": 1,
            "application_steps": ["step 1"],
        },
    )

    output = run_certification_agent(sector="textiles", target_countries=["US", "DE"])

    # Same two certs appear for both countries -- should be deduped, not doubled.
    names = [c.name for c in output.certifications]
    assert names.count("ISO 9001") == 1
    assert names.count("OEKO-TEX Standard 100") == 1


def test_certification_detail_fields_populated(monkeypatch):
    monkeypatch.setattr(
        "agents.certification_agent.get_capability_requirements",
        lambda sector, country: ["ISO 9001"],
    )
    monkeypatch.setattr(
        "agents.certification_agent.get_certification_details",
        lambda name: {
            "issuing_body": "BSI",
            "typical_cost_usd": (1500, 4000),
            "typical_timeline_weeks": (8, 16),
            "validity_years": 3,
            "application_steps": ["Gap analysis", "Audit"],
        },
    )

    output = run_certification_agent(sector="textiles", target_countries=["US"])
    cert = output.certifications[0]

    assert cert.issuing_body == "BSI"
    assert cert.cost_usd_range == (1500, 4000)
    assert cert.timeline_weeks_range == (8, 16)
    assert cert.validity_years == 3
    assert cert.application_steps == ["Gap analysis", "Audit"]


def test_for_name_lookup_works(monkeypatch):
    monkeypatch.setattr(
        "agents.certification_agent.get_capability_requirements",
        lambda sector, country: ["ISO 9001"],
    )
    monkeypatch.setattr(
        "agents.certification_agent.get_certification_details",
        lambda name: {
            "issuing_body": "Test",
            "typical_cost_usd": (100, 200),
            "typical_timeline_weeks": (1, 2),
            "validity_years": None,
            "application_steps": [],
        },
    )

    output = run_certification_agent(sector="textiles", target_countries=["US"])
    assert output.for_name("ISO 9001") is not None
    assert output.for_name("Nonexistent Cert") is None


def test_no_requirements_returns_empty_certifications(monkeypatch):
    monkeypatch.setattr(
        "agents.certification_agent.get_capability_requirements",
        lambda sector, country: [],
    )

    output = run_certification_agent(sector="textiles", target_countries=["US"])
    assert output.certifications == []
