"""
Query Parser for ExportAI
"""

import json
import re

from orchestrator.llm_provider import get_llm


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


def _detect_agents(query: str):

    query = query.lower()

    # Government schemes only
    if any(
        word in query
        for word in [
            "scheme",
            "schemes",
            "subsidy",
            "subsidies",
            "government",
            "benefit",
            "benefits",
            "rodtep",
            "pli",
            "incentive",
            "incentives",
        ]
    ):
        return [
            "scheme_compliance",
        ]

    # Default
    return [
        "demand_signal",
        "scheme_compliance",
    ]


def parse_query(
    query: str,
    provider=None,
) -> dict:

    llm = get_llm(provider)

    prompt = f"""
Return ONLY valid JSON.

Schema:

{{
    "sector":"",
    "target_countries":[],
    "hs_codes":[],
    "sme_revenue_cr":null
}}

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

    return {
        "sector": sector,
        "target_countries": countries,
        "hs_codes": hs_codes,
        "sme_revenue_cr": parsed.get(
            "sme_revenue_cr"
        ),
        "has_udyam_registration": True,
        "agents_to_call": _detect_agents(query),
    }