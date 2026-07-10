"""
Scheme/Compliance Agent.

A sub-agent responsible for matching a sector/SME profile to applicable
Indian government export schemes, and surfacing compliance requirements
for target markets.

Like the Demand Signal Agent, this is implemented as a deterministic
function (Pattern A from the template) rather than an LLM call —
eligibility matching against a knowledge base is a rules problem, not a
judgment problem. Compare this to the future Capability Gap Agent, which
*will* need an LLM because "does this certification partially satisfy
that requirement" is genuinely fuzzy.

This agent is intentionally cheap to run: no external API calls, no
per-request cost, since SCHEMES and COMPLIANCE_REQUIREMENTS are static
local data. That's also why it's the second agent built — it proves the
orchestrator can fan out to multiple sub-agents and merge their outputs
without needing a second paid data source yet.
"""

from dataclasses import dataclass, field

from data_sources.scheme_knowledge_base import (
    Scheme,
    get_compliance_requirements,
    get_schemes_for_sector,
)


@dataclass
class SchemeMatch:
    scheme_id: str
    name: str
    issuing_body: str
    benefit_summary: str
    eligible: bool
    eligibility_notes: str
    application_notes: str


@dataclass
class CountryCompliance:
    country: str
    requirements: list[str]


@dataclass
class SchemeComplianceAgentOutput:
    sector: str
    sme_revenue_cr: float | None
    matched_schemes: list[SchemeMatch] = field(default_factory=list)
    compliance_by_country: list[CountryCompliance] = field(default_factory=list)

    def eligible_schemes(self) -> list[SchemeMatch]:
        return [s for s in self.matched_schemes if s.eligible]


def _check_eligibility(
    scheme: Scheme, sme_revenue_cr: float | None, has_udyam: bool
) -> tuple[bool, str]:
    elig = scheme["eligibility"]

    if elig["requires_udyam_registration"] and not has_udyam:
        return False, "Requires Udyam registration (not on file for this SME)"

    if sme_revenue_cr is not None:
        if elig["max_revenue_cr"] is not None and sme_revenue_cr > elig["max_revenue_cr"]:
            return False, (
                f"SME revenue (\u20b9{sme_revenue_cr} Cr) exceeds scheme cap "
                f"of \u20b9{elig['max_revenue_cr']} Cr"
            )
        if sme_revenue_cr < elig["min_revenue_cr"]:
            return False, (
                f"SME revenue (\u20b9{sme_revenue_cr} Cr) below scheme minimum "
                f"of \u20b9{elig['min_revenue_cr']} Cr"
            )

    return True, "Meets sector and revenue-band eligibility criteria"


def run_scheme_compliance_agent(
    sector: str,
    target_countries: list[str],
    sme_revenue_cr: float | None = None,
    has_udyam_registration: bool = True,
) -> SchemeComplianceAgentOutput:
    """
    The Scheme/Compliance Agent's entry point. Matches schemes applicable
    to the sector and SME profile, and looks up compliance requirements
    for each target country.

    This is the function the orchestrator calls as a tool/node, in
    parallel with run_demand_signal_agent.
    """
    candidate_schemes = get_schemes_for_sector(sector)

    matched: list[SchemeMatch] = []
    for scheme in candidate_schemes:
        eligible, notes = _check_eligibility(
            scheme, sme_revenue_cr, has_udyam_registration
        )
        matched.append(
            SchemeMatch(
                scheme_id=scheme["scheme_id"],
                name=scheme["name"],
                issuing_body=scheme["issuing_body"],
                benefit_summary=scheme["benefit_summary"],
                eligible=eligible,
                eligibility_notes=notes,
                application_notes=scheme["application_notes"],
            )
        )

    # Sort eligible-first so the orchestrator/dashboard can show the
    # actionable ones up top without re-sorting.
    matched.sort(key=lambda m: not m.eligible)

    compliance = [
        CountryCompliance(
            country=country.upper(),
            requirements=get_compliance_requirements(country),
        )
        for country in target_countries
    ]

    return SchemeComplianceAgentOutput(
        sector=sector,
        sme_revenue_cr=sme_revenue_cr,
        matched_schemes=matched,
        compliance_by_country=compliance,
    )
