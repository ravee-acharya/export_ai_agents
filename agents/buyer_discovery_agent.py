"""
Buyer Discovery Agent.

Pattern B from agents/_template_agent.py: LLM-backed, like Capability
Gap. Identifying plausible buyer types for an SME's product in a given
market requires synthesizing knowledge about typical import/
distribution structures for a sector — a judgment call, not a lookup.

IMPORTANT — deliberate scope limit: this agent generates buyer
*personas* (categories like "mid-size home textile distributors" or
"hospitality linen procurement teams") and general outreach channels
(trade fairs, B2B platforms, sourcing agents), never specific named
companies. An LLM asked to name real buyer companies for a market it
has no live data on will hallucinate plausible-sounding but fabricated
names — that's actively harmful advice for someone making real
business decisions. The prompt explicitly forbids this, and the
fallback path never invents company names either.
"""

import json
import re
from dataclasses import dataclass, field

from orchestrator.llm_provider import get_llm


@dataclass
class BuyerPersona:
    persona_name: str
    description: str
    typical_order_size: str
    procurement_notes: str


@dataclass
class BuyerDiscoveryOutput:
    sector: str
    target_countries: list[str]
    buyer_personas: list[BuyerPersona] = field(default_factory=list)
    recommended_channels: list[str] = field(default_factory=list)
    outreach_tips: list[str] = field(default_factory=list)
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


# Conservative, generic fallback used only if the LLM call or parsing
# fails — still useful, still never names specific companies.
_FALLBACK_CHANNELS = [
    "Sector-specific trade fairs and exhibitions",
    "B2B sourcing platforms (e.g. Alibaba, IndiaMART, TradeIndia)",
    "Export promotion council buyer-seller meets",
    "Sourcing agents/trading houses with existing buyer relationships",
]


def run_buyer_discovery_agent(
    sector: str,
    target_countries: list[str],
    hs_codes: list[str] | None = None,
    provider: str | None = None,
) -> BuyerDiscoveryOutput:
    """
    The Buyer Discovery Agent's entry point, called by the orchestrator
    like any other sub-agent. Never raises — on LLM/parsing failure it
    returns a generic-but-honest fallback (general channels, no
    fabricated personas or companies) rather than crashing the graph.
    """
    hs_codes = hs_codes or []
    llm = get_llm(provider)

    from prompts.manager import render_prompt
    prompt = render_prompt(
        "buyer_discovery",
        sector=sector,
        hs_codes=json.dumps(hs_codes),
        target_countries=", ".join(target_countries),
    )

    try:
        response = llm.invoke(prompt)
        try:
            from orchestrator.token_tracker import record_usage
            record_usage("buyer_discovery", response)
        except Exception:
            pass
        parsed = _extract_json(response.content)

        personas = [
            BuyerPersona(
                persona_name=p.get("persona_name", "Unnamed persona"),
                description=p.get("description", ""),
                typical_order_size=p.get("typical_order_size", ""),
                procurement_notes=p.get("procurement_notes", ""),
            )
            for p in parsed.get("buyer_personas", [])
        ]

        return BuyerDiscoveryOutput(
            sector=sector,
            target_countries=target_countries,
            buyer_personas=personas,
            recommended_channels=parsed.get(
                "recommended_channels", _FALLBACK_CHANNELS
            ),
            outreach_tips=parsed.get("outreach_tips", []),
            reasoning=parsed.get("reasoning", ""),
        )

    except Exception as ex:
        return BuyerDiscoveryOutput(
            sector=sector,
            target_countries=target_countries,
            buyer_personas=[],
            recommended_channels=_FALLBACK_CHANNELS,
            outreach_tips=[],
            reasoning=f"Detailed persona generation unavailable: {ex}",
        )
