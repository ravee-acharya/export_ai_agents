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
    ],
    "ceramics": [
        "ceramic",
        "ceramics",
        "tile",
        "tiles",
        "vitrified",
        "porcelain",
        "sanitaryware",
        "sanitary ware",
        "crockery",
        "tableware",
    ],
    "leather": [
        "leather",
        "footwear",
        "shoes",
        "leather goods",
        "handbag",
        "handbags",
    ],
    "engineering": [
        "engineering goods",
        "auto parts",
        "auto component",
        "machinery",
        "casting",
        "forging",
        "hardware",
    ],
    "chemicals": [
        "chemical",
        "chemicals",
        "dye",
        "dyes",
        "pigment",
        "pigments",
        "agrochemical",
        "specialty chemical",
    ],
    "gems_jewellery": [
        "jewellery",
        "jewelry",
        "gems",
        "diamond",
        "diamonds",
        "gold jewellery",
    ],
}

DEFAULT_HS_CODES = {
    "textiles": [
        "6302",
        "5911",
        "6204",
    ],
    "ceramics": [
        "6907",  # ceramic flags/tiles, unglazed
        "6908",  # ceramic flags/tiles, glazed
        "6910",  # ceramic sinks/sanitaryware
    ],
    "leather": [
        "4202",
        "6403",
        "4107",
    ],
    "engineering": [
        "8708",  # auto parts
        "7325",  # cast articles of iron/steel
        "8483",  # transmission/gears
    ],
    "chemicals": [
        "3204",  # synthetic dyes
        "2942",  # organic chemicals
        "3808",  # agrochemicals
    ],
    "gems_jewellery": [
        "7113",  # jewellery of precious metal
        "7102",  # diamonds
    ],
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
    """
    Map a sector to one of our known canonical categories when possible
    (so DEFAULT_HS_CODES and capability_requirements lookups work), but
    NEVER silently overwrite a real sector the LLM already extracted
    just because it doesn't match a known keyword list. Forcing an
    unrecognized sector (e.g. "ceramics") into "textiles" produces
    confidently wrong answers, which is worse than an unmapped sector
    that still gets used for downstream reasoning.

    Resolution order:
      1. If `sector` is given and matches a known canonical/keyword,
         return that canonical name.
      2. If `sector` is given but doesn't match anything known, return
         it as-is (cleaned) rather than discarding it.
      3. If `sector` is empty, try to detect a canonical sector from
         keywords in the raw query text.
      4. Only if nothing at all could be determined, fall back to
         "textiles" (the sector with the most complete supporting data).
    """

    if sector:

        sector = sector.lower().strip()

        for canonical, keywords in SECTOR_KEYWORDS.items():

            # Substring containment, not exact equality: the LLM often
            # extracts a descriptive phrase (e.g. "tiles and ceramics
            # manufacturing") rather than a bare keyword. Exact equality
            # against SECTOR_KEYWORDS entries would miss that phrase
            # entirely and silently fall through to "return sector"
            # below, breaking every exact-key lookup downstream
            # (DEFAULT_HS_CODES, capability_requirements, etc.) that
            # expects the canonical name.
            if sector == canonical:
                return canonical
            if any(keyword in sector for keyword in keywords):
                return canonical

        # Not a known canonical sector, but the LLM did extract
        # something specific -- trust it rather than overwriting.
        return sector

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

    from prompts.manager import render_prompt
    context_block = (
        render_prompt("query_parser_context_block",
                      conversation_context=conversation_context)
        if conversation_context
        else ""
    )

    prompt = render_prompt(
        "query_parser",
        context_block=context_block,
        available_agents=available_agents,
        query=query,
    )

    response = llm.invoke(prompt)
    try:
        from orchestrator.token_tracker import record_usage
        record_usage("query_parser", response)
    except Exception:
        pass

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