"""
Query Parser for ExportAI
"""

import json
import re

from orchestrator.llm_provider import get_llm
from orchestrator.registry import detect_agents_from_query, AGENT_REGISTRY


COUNTRY_MAP = {
    "germany": "DE",
    "deutschland": "DE",
    "france": "FR",
    "italy": "IT",
    "spain": "ES",
    "netherlands": "NL",
    "belgium": "BE",
    "united kingdom": "GB",
    "uk": "GB",
    "england": "GB",
    "great britain": "GB",
    "united states": "US",
    "usa": "US",
    "america": "US",
    "canada": "CA",
    "australia": "AU",
    "japan": "JP",
    "uae": "AE",
    "united arab emirates": "AE",
    "singapore": "SG",
}

SECTOR_KEYWORDS = {
    "textiles": [
        "textile",
        "textiles",
        "garment",
        "garments",
        "apparel",
        "cotton",
        "fabric",
        "towel",
        "towels",
        "home textile",
        "bed linen",
        "linen",
    ]
}

DEFAULT_HS_CODES = {
    "textiles": [
        "6302",
        "5911",
        "6204",
    ]
}


def _extract_json(text: str) -> dict:
    text = text.replace("```json", "")
    text = text.replace("```", "")
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        raise ValueError("Unable to extract JSON.")

    return json.loads(match.group(0))


def _normalize_sector(sector, query):

    if sector:

        sector = sector.lower().strip()

        for canonical, keywords in SECTOR_KEYWORDS.items():

            if sector == canonical or sector in keywords:
                return canonical

    query = query.lower()

    for canonical, keywords in SECTOR_KEYWORDS.items():

        if any(word in query for word in keywords):
            return canonical

    return "textiles"


def _normalize_countries(countries):

    output = []

    for country in countries or []:

        output.append(
            COUNTRY_MAP.get(
                country.strip().lower(),
                country.strip().upper(),
            )
        )

    return list(dict.fromkeys(output))


def _validate_agent_selection(candidate) -> list[str] | None:
    """
    The LLM-proposed agent list is only trusted if it's a non-empty
    list of strings that are all real, registered agent names.
    Anything else (missing, wrong type, hallucinated agent name,
    empty list) falls back to keyword-based detection rather than
    silently running zero agents or crashing on an unknown key.
    """
    if not isinstance(candidate, list) or not candidate:
        return None
    if not all(isinstance(name, str) for name in candidate):
        return None
    if not all(name in AGENT_REGISTRY for name in candidate):
        return None
    return candidate


def parse_query(
    query: str,
    provider=None,
    conversation_context: str = "",
) -> dict:

    llm = get_llm(provider)

    available_agents = ", ".join(AGENT_REGISTRY.keys())

    context_block = (
        f"""
Prior conversation context (use this to fill in sector/countries/HS
codes if the current query doesn't restate them -- e.g. a follow-up
question like "what about the certification costs?" should inherit
the sector and countries from the prior turn below, not leave them
empty):

{conversation_context}
"""
        if conversation_context
        else ""
    )

    prompt = f"""
Return ONLY valid JSON.
{context_block}
Schema:

{{
    "sector":"",
    "target_countries":[],
    "hs_codes":[],
    "sme_revenue_cr":null,
    "relevant_agents":[]
}}

For "relevant_agents", choose only from this exact list of available
agents based on what the query is actually asking about: {available_agents}

If the query is a general export opportunity question (not narrowly
about one topic), include all of them. If it's narrowly about one
topic (e.g. only asking about government schemes), include only the
agent(s) that answer that specific question.

If the current query is a follow-up that doesn't restate sector or
target countries (e.g. "what about pricing?" or "what certifications
would I need?"), infer them from the prior conversation context above
rather than leaving target_countries empty.

Query:

{query}
"""

    response = llm.invoke(prompt)

    parsed = _extract_json(response.content)

    sector = _normalize_sector(
        parsed.get("sector"),
        query,
    )

    countries = _normalize_countries(
        parsed.get(
            "target_countries",
            [],
        )
    )

    hs_codes = parsed.get("hs_codes")

    if not hs_codes:
        hs_codes = DEFAULT_HS_CODES.get(
            sector,
            [],
        )

    # Prefer the LLM's own agent selection (it has the actual query's
    # semantics available, not just keyword matches) -- but only if it
    # passes validation. Keyword-based detection remains the fallback,
    # never removed, so a bad/missing LLM response never breaks agent
    # selection entirely.
    llm_agents = _validate_agent_selection(parsed.get("relevant_agents"))
    agents_to_call = llm_agents if llm_agents is not None else detect_agents_from_query(query)

    return {
        "sector": sector,
        "target_countries": countries,
        "hs_codes": hs_codes,
        "sme_revenue_cr": parsed.get(
            "sme_revenue_cr"
        ),
        "has_udyam_registration": True,
        "agents_to_call": agents_to_call,
    }