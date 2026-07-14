"""
Mock country risk knowledge base. Stand-in for real risk data sources
(e.g. ECGC country risk classifications, Coface/Moody's country risk
ratings, OFAC sanctions lists) until one is integrated.

Deterministic lookup data, like logistics_data.py and
scheme_knowledge_base.py — no judgment call involved, so this backs a
Pattern A agent, not an LLM-backed one.
"""

# political_risk: 0 (stable) - 1 (high political/trade risk)
# currency_volatility: 0 (stable currency) - 1 (highly volatile)
# payment_default_risk: 0 (reliable payment) - 1 (high default risk)
# sanctions_flag: True if the country has active trade sanctions/restrictions
#   relevant to Indian exporters
# ecgc_cover_available: whether ECGC (Export Credit Guarantee Corporation)
#   typically offers cover for this market
_RISK_DATA = {
    "US": {
        "political_risk": 0.15,
        "currency_volatility": 0.20,
        "payment_default_risk": 0.10,
        "sanctions_flag": False,
        "ecgc_cover_available": True,
        "notes": "Stable market, standard ECGC cover available.",
    },
    "DE": {
        "political_risk": 0.10,
        "currency_volatility": 0.15,
        "payment_default_risk": 0.08,
        "sanctions_flag": False,
        "ecgc_cover_available": True,
        "notes": "EU market, strong payment reliability.",
    },
    "GB": {
        "political_risk": 0.15,
        "currency_volatility": 0.25,
        "payment_default_risk": 0.10,
        "sanctions_flag": False,
        "ecgc_cover_available": True,
        "notes": "Stable, some currency volatility post-Brexit.",
    },
    "CA": {
        "political_risk": 0.10,
        "currency_volatility": 0.20,
        "payment_default_risk": 0.08,
        "sanctions_flag": False,
        "ecgc_cover_available": True,
        "notes": "Stable market, reliable payment terms.",
    },
    "AU": {
        "political_risk": 0.10,
        "currency_volatility": 0.25,
        "payment_default_risk": 0.10,
        "sanctions_flag": False,
        "ecgc_cover_available": True,
        "notes": "Stable, moderate currency swings.",
    },
    "AE": {
        "political_risk": 0.25,
        "currency_volatility": 0.10,
        "payment_default_risk": 0.20,
        "sanctions_flag": False,
        "ecgc_cover_available": True,
        "notes": "Currency pegged to USD, low volatility. Verify buyer creditworthiness.",
    },
    "SG": {
        "political_risk": 0.10,
        "currency_volatility": 0.15,
        "payment_default_risk": 0.08,
        "sanctions_flag": False,
        "ecgc_cover_available": True,
        "notes": "Stable financial hub, strong payment reliability.",
    },
}

# Used when a country isn't in the table above — conservative defaults
# rather than assuming low risk for an unknown market.
_DEFAULT_RISK = {
    "political_risk": 0.45,
    "currency_volatility": 0.40,
    "payment_default_risk": 0.35,
    "sanctions_flag": False,
    "ecgc_cover_available": False,
    "notes": "No risk data on file for this market — verify manually before proceeding.",
}


def get_risk_data(country: str) -> dict:
    return _RISK_DATA.get(country.upper(), _DEFAULT_RISK)
