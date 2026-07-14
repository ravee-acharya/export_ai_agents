"""
Document Intelligence Agent.

Pattern A from agents/_template_agent.py: deterministic lookup, like
Scheme/Compliance, Logistics, Risk, Competitor, and Tariff & FTA. Which
customs/shipping documents a market requires is reference data
(published customs authority requirements), not a judgment call.

Deliberately scoped to customs/shipping PAPERWORK (commercial invoice,
packing list, bill of lading, certificate of origin, etc.) -- not
product certifications or quality standards, which the Capability Gap
Agent already covers. This keeps the two agents answering distinct
questions rather than overlapping: Capability Gap asks "is the SME's
product/process ready for this market's standards", this agent asks
"what paperwork does the shipment itself need".

Like Scheme/Compliance and Risk, this agent's output does NOT feed the
opportunity scoring formula -- it's operational/checklist information
for executing an export, not a factor in whether the opportunity is
worth pursuing.
"""

from dataclasses import dataclass, field

from data_sources.document_requirements import get_document_requirements


@dataclass
class ConditionalDocument:
    name: str
    condition: str


@dataclass
class DocumentChecklist:
    destination_country: str
    mandatory_documents: list[str]
    conditional_documents: list[ConditionalDocument]
    notes: str


@dataclass
class DocumentIntelligenceOutput:
    sector: str
    checklists: list[DocumentChecklist] = field(default_factory=list)

    def for_country(self, country: str) -> DocumentChecklist | None:
        country = country.upper()
        for checklist in self.checklists:
            if checklist.destination_country == country:
                return checklist
        return None


def run_document_intelligence_agent(
    sector: str,
    target_countries: list[str],
) -> DocumentIntelligenceOutput:
    """
    The Document Intelligence Agent's entry point, called by the
    orchestrator like any other sub-agent. Modeled per destination
    country -- document requirements are driven by the importing
    country's customs authority, not the HS code or sector in this
    mock data, so every target country gets exactly one checklist.
    """
    checklists: list[DocumentChecklist] = []

    for country in target_countries:
        data = get_document_requirements(country)

        conditional = [
            ConditionalDocument(name=c["name"], condition=c["condition"])
            for c in data["conditional"]
        ]

        checklists.append(
            DocumentChecklist(
                destination_country=country.upper(),
                mandatory_documents=data["mandatory"],
                conditional_documents=conditional,
                notes=data["notes"],
            )
        )

    return DocumentIntelligenceOutput(sector=sector, checklists=checklists)
