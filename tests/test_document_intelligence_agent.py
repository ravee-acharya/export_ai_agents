"""
Unit tests for agents/document_intelligence_agent.py.

Monkeypatches get_document_requirements so these tests verify the
agent's own structuring logic, not the specific mock document lists.
"""

from agents.document_intelligence_agent import run_document_intelligence_agent


def _fake_requirements(mandatory, conditional=None, notes="test notes"):
    return lambda country: {
        "mandatory": mandatory,
        "conditional": conditional or [],
        "notes": notes,
    }


def test_mandatory_documents_passed_through(monkeypatch):
    monkeypatch.setattr(
        "agents.document_intelligence_agent.get_document_requirements",
        _fake_requirements(["Commercial Invoice", "Packing List"]),
    )

    output = run_document_intelligence_agent(sector="textiles", target_countries=["US"])
    checklist = output.checklists[0]

    assert checklist.mandatory_documents == ["Commercial Invoice", "Packing List"]


def test_conditional_documents_structured_correctly(monkeypatch):
    monkeypatch.setattr(
        "agents.document_intelligence_agent.get_document_requirements",
        _fake_requirements(
            ["Commercial Invoice"],
            conditional=[{"name": "FDA Notice", "condition": "If FDA-regulated"}],
        ),
    )

    output = run_document_intelligence_agent(sector="textiles", target_countries=["US"])
    checklist = output.checklists[0]

    assert len(checklist.conditional_documents) == 1
    assert checklist.conditional_documents[0].name == "FDA Notice"
    assert checklist.conditional_documents[0].condition == "If FDA-regulated"


def test_no_conditional_documents_returns_empty_list(monkeypatch):
    monkeypatch.setattr(
        "agents.document_intelligence_agent.get_document_requirements",
        _fake_requirements(["Commercial Invoice"]),
    )

    output = run_document_intelligence_agent(sector="textiles", target_countries=["US"])
    assert output.checklists[0].conditional_documents == []


def test_for_country_lookup_works(monkeypatch):
    monkeypatch.setattr(
        "agents.document_intelligence_agent.get_document_requirements",
        _fake_requirements(["Commercial Invoice"]),
    )

    output = run_document_intelligence_agent(sector="textiles", target_countries=["US"])
    checklist = output.for_country("US")

    assert checklist is not None
    assert checklist.destination_country == "US"


def test_for_country_case_insensitive(monkeypatch):
    monkeypatch.setattr(
        "agents.document_intelligence_agent.get_document_requirements",
        _fake_requirements(["Commercial Invoice"]),
    )

    output = run_document_intelligence_agent(sector="textiles", target_countries=["us"])
    assert output.for_country("US") is not None
    assert output.for_country("us") is not None


def test_for_country_returns_none_when_absent(monkeypatch):
    monkeypatch.setattr(
        "agents.document_intelligence_agent.get_document_requirements",
        _fake_requirements(["Commercial Invoice"]),
    )

    output = run_document_intelligence_agent(sector="textiles", target_countries=["US"])
    assert output.for_country("ZZ") is None


def test_every_target_country_gets_exactly_one_checklist(monkeypatch):
    monkeypatch.setattr(
        "agents.document_intelligence_agent.get_document_requirements",
        _fake_requirements(["Commercial Invoice"]),
    )

    output = run_document_intelligence_agent(
        sector="textiles", target_countries=["US", "DE", "AE"]
    )

    assert len(output.checklists) == 3
    countries = {c.destination_country for c in output.checklists}
    assert countries == {"US", "DE", "AE"}


def test_notes_passed_through(monkeypatch):
    monkeypatch.setattr(
        "agents.document_intelligence_agent.get_document_requirements",
        _fake_requirements(["Commercial Invoice"], notes="Custom test note"),
    )

    output = run_document_intelligence_agent(sector="textiles", target_countries=["US"])
    assert output.checklists[0].notes == "Custom test note"
