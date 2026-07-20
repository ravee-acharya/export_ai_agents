"""
Country risk reference data for Indian exporters.

Sources used to compile this data:
  - ECGC (Export Credit Guarantee Corporation) country risk classifications
    https://www.ecgc.in/
  - World Bank Worldwide Governance Indicators (political stability)
  - IMF exchange rate volatility assessments
  - OFAC SDN list for sanctions flags
  - RBI guidelines on payment terms for high-risk markets

Update cadence: quarterly, or on major geopolitical events.
Last updated: July 2026

Not a live API — country risk fundamentals change slowly enough that
a well-maintained static table is more reliable than a scraped feed.
When a new key market needs to be added, add it here.
"""

_RISK_DATA: dict[str, dict] = {
    "US": {
        "political_risk": 0.12, "currency_volatility": 0.18,
        "payment_default_risk": 0.08, "sanctions_flag": False,
        "ecgc_cover_available": True,
        "ecgc_category": "A1",
        "notes": "Most stable export market. Standard 30/60-day payment terms routine. "
                 "ECGC A1 — full cover available.",
    },
    "DE": {
        "political_risk": 0.10, "currency_volatility": 0.14,
        "payment_default_risk": 0.07, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "A1",
        "notes": "Euro zone, strong SME import culture. LC at sight standard for new relationships.",
    },
    "GB": {
        "political_risk": 0.14, "currency_volatility": 0.22,
        "payment_default_risk": 0.09, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "A1",
        "notes": "GBP volatility elevated post-Brexit. ECGC cover available.",
    },
    "CA": {
        "political_risk": 0.11, "currency_volatility": 0.19,
        "payment_default_risk": 0.08, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "A1",
        "notes": "Stable, close US market relationship. CAD tracks USD closely.",
    },
    "AU": {
        "political_risk": 0.10, "currency_volatility": 0.21,
        "payment_default_risk": 0.08, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "A1",
        "notes": "AUD can be volatile vs INR. Strong India-Australia ECTA in force.",
    },
    "AE": {
        "political_risk": 0.18, "currency_volatility": 0.05,
        "payment_default_risk": 0.12, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "A2",
        "notes": "AED is USD-pegged (minimal FX risk). Re-export hub — verify actual end-user. "
                 "India-UAE CEPA provides preferential tariff access.",
    },
    "SG": {
        "political_risk": 0.08, "currency_volatility": 0.12,
        "payment_default_risk": 0.06, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "A1",
        "notes": "Top-rated market. ASEAN re-export hub. CECA in force with India.",
    },
    "JP": {
        "political_risk": 0.09, "currency_volatility": 0.25,
        "payment_default_risk": 0.07, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "A1",
        "notes": "JPY has been volatile. Quality standards very high — certification critical. "
                 "Japan-India CEPA in force.",
    },
    "FR": {
        "political_risk": 0.13, "currency_volatility": 0.14,
        "payment_default_risk": 0.09, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "A1",
        "notes": "EU market access via EUSFTA. Standard EU import documentation applies.",
    },
    "IT": {
        "political_risk": 0.18, "currency_volatility": 0.14,
        "payment_default_risk": 0.14, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "A2",
        "notes": "Slightly elevated payment default risk vs northern EU. Confirm LC terms.",
    },
    "NL": {
        "political_risk": 0.09, "currency_volatility": 0.14,
        "payment_default_risk": 0.07, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "A1",
        "notes": "Rotterdam gateway for EU. Strong distribution hub.",
    },
    "ES": {
        "political_risk": 0.16, "currency_volatility": 0.14,
        "payment_default_risk": 0.12, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "A2",
        "notes": "Moderate payment risk. Growing import market for textiles/leather.",
    },
    "BE": {
        "political_risk": 0.11, "currency_volatility": 0.14,
        "payment_default_risk": 0.08, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "A1",
        "notes": "Antwerp port is key EU entry. Standard EU documentation.",
    },
    "CN": {
        "political_risk": 0.32, "currency_volatility": 0.15,
        "payment_default_risk": 0.18, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "B",
        "notes": "Geopolitical tensions. Payment via LC strongly recommended. "
                 "IP protection requires caution on design-sensitive products.",
    },
    "KR": {
        "political_risk": 0.20, "currency_volatility": 0.20,
        "payment_default_risk": 0.10, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "A2",
        "notes": "CEPA in force. KRW volatility moderate. Strong quality expectations.",
    },
    "BR": {
        "political_risk": 0.38, "currency_volatility": 0.40,
        "payment_default_risk": 0.25, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "C",
        "notes": "BRL highly volatile. High import duties and complex customs. "
                 "ECGC C category — limited cover, confirm terms carefully.",
    },
    "ZA": {
        "political_risk": 0.42, "currency_volatility": 0.35,
        "payment_default_risk": 0.28, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "C",
        "notes": "ZAR volatile. ECGC C category. Confirm buyer creditworthiness.",
    },
    "SA": {
        "political_risk": 0.28, "currency_volatility": 0.05,
        "payment_default_risk": 0.15, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "B",
        "notes": "SAR is USD-pegged. Strong purchasing power. Government project payments can be slow.",
    },
    "RU": {
        "political_risk": 0.85, "currency_volatility": 0.60,
        "payment_default_risk": 0.65, "sanctions_flag": True,
        "ecgc_cover_available": False, "ecgc_category": "D",
        "notes": "OFAC/EU/UK sanctions in force. Payment via USD/SWIFT severely restricted. "
                 "ECGC does not provide cover. Consult RBI/DGFT before exporting.",
    },
    "NG": {
        "political_risk": 0.55, "currency_volatility": 0.55,
        "payment_default_risk": 0.45, "sanctions_flag": False,
        "ecgc_cover_available": True, "ecgc_category": "D",
        "notes": "NGN very volatile. Forex repatriation delays common. Irrevocable LC essential.",
    },
}

_DEFAULT_RISK = {
    "political_risk": 0.40, "currency_volatility": 0.35,
    "payment_default_risk": 0.30, "sanctions_flag": False,
    "ecgc_cover_available": True, "ecgc_category": "C",
    "notes": "No specific risk data on file. Conservative defaults applied.",
}


def get_risk_data(country: str) -> dict:
    return _RISK_DATA.get(country.upper(), _DEFAULT_RISK)
