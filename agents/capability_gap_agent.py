"""
Capability Gap Agent.

Pattern B from agents/_template_agent.py: this is an LLM-backed
sub-agent, not a deterministic one like Demand Signal or Scheme/
Compliance. Whether an SME's existing certifications "cover enough" of
a target market's requirements is a fuzzy matching/judgment call (e.g.
does an ISO 9001 certificate partially satisfy a BSCI-style social
compliance requirement?) — that's not something a lookup table can
answer reliably.

Output feeds directly into the opportunity scoring formula as
capability_distance (0-1, higher = bigger gap = worse for scoring),
replacing the PLACEHOLDER_CAPABILITY_DISTANCE constant in scorer.py.
"""

import json
import re
from dataclasses import dataclass, field

from data_sources.capability_requirements import get_capability_requirements
from orchestrator.llm_provider import get_llm


@dataclass
class CapabilityGapAgentOutput:
    sector: str
    target_countries: list[str]
    gap_score: int  # 1 (fully capable) to 5 (large gap)
    capability_distance: float  # 0-1, derived from gap_score, used in scoring
    missing_requirements: list[str] = field(default_factory=list)
    upgrade_path: list[str] = field(default_factory=list)
    reasoning: str = ""


def _extract_json(text: str) -> dict:
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Unable to extract JSON from LLM response.")
    return json.loads(match.group(0))


def _gap_score_to_distance(gap_score: int) -> float:
    # 1 -> 0.0 (no gap), 5 -> 1.0 (large gap)
    gap_score = max(1, min(5, gap_score))
    return round((gap_score - 1) / 4, 2)


def run_capability_gap_agent(
    sector: str,
    target_countries: list[str],
    sme_certifications: list[str] | None = None,
    provider: str | None = None,
) -> CapabilityGapAgentOutput:
    """
    The Capability Gap Agent's entry point, called by the orchestrator
    like any other sub-agent. Never raises — on LLM/parsing failure it
    returns a conservative fallback (see except block) so one agent's
    failure doesn't crash the whole graph run (mirrors _safe_call's
    contract in dispatcher.py, but the agent itself stays defensive
    too since it may be called outside the orchestrator, e.g. in tests).
    """
    sme_certifications = sme_certifications or []

    requirements_by_country = {
        country: get_capability_requirements(sector, country)
        for country in target_countries
    }

    all_requirements = sorted(
        {req for reqs in requirements_by_country.values() for req in reqs}
    )

    llm = get_llm(provider)

    from prompts.manager import render_prompt
    prompt = render_prompt(
        "capability_gap",
        sector=sector,
        target_countries=", ".join(target_countries),
        sme_certifications=json.dumps(sme_certifications),
        all_requirements=json.dumps(all_requirements),
    )

    try:
        response = llm.invoke(prompt)
        try:
            from orchestrator.token_tracker import record_usage
            record_usage("capability_gap", response)
        except Exception:
            pass
        parsed = _extract_json(response.content)

        gap_score = int(parsed.get("gap_score", 3))

        return CapabilityGapAgentOutput(
            sector=sector,
            target_countries=target_countries,
            gap_score=gap_score,
            capability_distance=_gap_score_to_distance(gap_score),
            missing_requirements=parsed.get("missing_requirements", []),
            upgrade_path=parsed.get("upgrade_path", []),
            reasoning=parsed.get("reasoning", ""),
        )

    except Exception as ex:
        # Conservative fallback: assume a moderate gap rather than
        # crashing the graph or silently claiming zero gap.
        return CapabilityGapAgentOutput(
            sector=sector,
            target_countries=target_countries,
            gap_score=3,
            capability_distance=0.5,
            missing_requirements=all_requirements,
            upgrade_path=[],
            reasoning=f"Assessment unavailable, defaulted to moderate gap: {ex}",
        )
