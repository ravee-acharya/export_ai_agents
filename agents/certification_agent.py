"""
Certification Agent.

Pattern A from agents/_template_agent.py: deterministic lookup, like
Scheme/Compliance, Logistics, Risk, Competitor, Tariff & FTA, and
Document Intelligence. Certification cost/timeline/process is
reference data, not a judgment call.

Deliberately distinct from the Capability Gap Agent: that agent
answers "which certifications does this SME need, and how big is the
gap" (a judgment call about fit, hence LLM-backed). This agent answers
a different, purely factual question -- "for a given certification,
what's the process, cost, and timeline to actually obtain it." Kept as
a separate agent rather than folded into Capability Gap because the
two questions have genuinely different answer types (judgment vs.
lookup) and merging them would force the deterministic process data
through an LLM call it doesn't need.

Sourced from the same sector+country requirement list as Capability
Gap (via capability_requirements.py) rather than depending on
Capability Gap's live output, since agents in this registry are
independent by design and don't read each other's dispatch-time
results.
"""

from dataclasses import dataclass, field

from data_sources.capability_requirements import get_capability_requirements
from data_sources.certification_details import get_certification_details


@dataclass
class CertificationProcess:
    name: str
    issuing_body: str
    cost_usd_range: tuple[float, float]
    timeline_weeks_range: tuple[float, float]
    validity_years: float | None
    application_steps: list[str]


@dataclass
class CertificationAgentOutput:
    sector: str
    certifications: list[CertificationProcess] = field(default_factory=list)

    def for_name(self, name: str) -> CertificationProcess | None:
        for c in self.certifications:
            if c.name == name:
                return c
        return None


def run_certification_agent(
    sector: str,
    target_countries: list[str],
) -> CertificationAgentOutput:
    """
    The Certification Agent's entry point, called by the orchestrator
    like any other sub-agent. Collects the distinct set of
    certifications relevant across all target countries for this
    sector, then looks up the process/cost/timeline for each.
    """
    all_requirements = sorted(
        {
            req
            for country in target_countries
            for req in get_capability_requirements(sector, country)
        }
    )

    certifications = []
    for name in all_requirements:
        detail = get_certification_details(name)
        certifications.append(
            CertificationProcess(
                name=name,
                issuing_body=detail["issuing_body"],
                cost_usd_range=detail["typical_cost_usd"],
                timeline_weeks_range=detail["typical_timeline_weeks"],
                validity_years=detail["validity_years"],
                application_steps=detail["application_steps"],
            )
        )

    return CertificationAgentOutput(sector=sector, certifications=certifications)
