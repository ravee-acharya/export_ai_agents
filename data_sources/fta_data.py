"""
Mock FTA (Free Trade Agreement) and tariff data, including special
duties (anti-dumping/countervailing) that apply regardless of FTA
status. Stand-in for a real source (e.g. DGFT's FTA tariff schedules,
DGTR anti-dumping notifications, WTO Tariff Analysis Online) until one
is integrated.

Deterministic lookup data, like scheme_knowledge_base.py and
risk_data.py -- FTA eligibility, MFN rates, and special duties are all
reference data, not a judgment call, so this backs a Pattern A agent.

Special duties (anti-dumping, countervailing, safeguard) are modeled
separately from the FTA/MFN tariff because they apply independently of
trade agreement status -- an FTA can zero out the standard tariff while
a special duty (imposed for a specific reason, like a dumping finding)
still applies on top of it.
"""

# Each FTA country entry: the agreement name, rules-of-origin summary,
# and per-HS-code MFN (most-favored-nation, i.e. standard) vs.
# preferential tariff rates under the agreement.
_FTA_COUNTRIES = {
    "AE": {
        "fta_name": "India-UAE CEPA",
        "rules_of_origin": (
            "Minimum 35% domestic value addition + change in tariff "
            "heading at the 4-digit level."
        ),
        "tariff_rates": {
            "6302": {"mfn_pct": 5.0, "preferential_pct": 0.0},
            "5911": {"mfn_pct": 5.0, "preferential_pct": 0.0},
            "6204": {"mfn_pct": 5.0, "preferential_pct": 0.0},
        },
    },
    "SG": {
        "fta_name": "India-Singapore CECA",
        "rules_of_origin": (
            "Minimum 40% domestic value addition + change in tariff "
            "subheading."
        ),
        "tariff_rates": {
            "6302": {"mfn_pct": 4.0, "preferential_pct": 0.0},
            "5911": {"mfn_pct": 4.0, "preferential_pct": 0.0},
        },
    },
}

# Countries with no active bilateral/regional FTA with India in this
# mock dataset -- exporters pay standard MFN rates only.
_DEFAULT_MFN_TARIFF_PCT = {
    "US": 8.0,
    "DE": 10.0,  # EU common external tariff; India-EU FTA still under
                 # negotiation as of this mock data, so no preferential rate.
    "GB": 9.5,
    "CA": 8.5,
    "AU": 5.0,
}

# Used for any country/HS combination not explicitly listed above.
_FALLBACK_MFN_TARIFF_PCT = 10.0

# Anti-dumping/countervailing/safeguard duties, keyed by (hs_code,
# country). These apply on top of the FTA/MFN rate regardless of trade
# agreement status. Empty for a pair means no special duty is in
# effect for that combination in this mock dataset.
_SPECIAL_DUTIES = {
    ("5911", "US"): {
        "anti_dumping_duty_pct": 6.5,
        "countervailing_duty_pct": 0.0,
        "notes": (
            "Anti-dumping duty in effect on certain technical textile "
            "imports from India in this mock dataset -- verify current "
            "status with DGFT/US Customs before relying on this figure."
        ),
    },
}


def get_fta_info(hs_code: str, country: str) -> dict:
    country = country.upper()
    entry = _FTA_COUNTRIES.get(country)

    special = _SPECIAL_DUTIES.get((hs_code, country), {})
    anti_dumping_pct = special.get("anti_dumping_duty_pct", 0.0)
    countervailing_pct = special.get("countervailing_duty_pct", 0.0)
    special_notes = special.get("notes")

    if entry is None:
        return {
            "fta_name": None,
            "mfn_tariff_pct": _DEFAULT_MFN_TARIFF_PCT.get(
                country, _FALLBACK_MFN_TARIFF_PCT
            ),
            "preferential_tariff_pct": None,
            "rules_of_origin": None,
            "anti_dumping_duty_pct": anti_dumping_pct,
            "countervailing_duty_pct": countervailing_pct,
            "special_duty_notes": special_notes,
        }

    rates = entry["tariff_rates"].get(hs_code)

    if rates is None:
        # Country has an FTA with India, but this specific HS code
        # isn't in its preferential schedule (or not yet in our mock
        # data) -- exporter still pays MFN for this product.
        return {
            "fta_name": entry["fta_name"],
            "mfn_tariff_pct": _FALLBACK_MFN_TARIFF_PCT,
            "preferential_tariff_pct": None,
            "rules_of_origin": entry["rules_of_origin"],
            "anti_dumping_duty_pct": anti_dumping_pct,
            "countervailing_duty_pct": countervailing_pct,
            "special_duty_notes": special_notes,
        }

    return {
        "fta_name": entry["fta_name"],
        "mfn_tariff_pct": rates["mfn_pct"],
        "preferential_tariff_pct": rates["preferential_pct"],
        "rules_of_origin": entry["rules_of_origin"],
        "anti_dumping_duty_pct": anti_dumping_pct,
        "countervailing_duty_pct": countervailing_pct,
        "special_duty_notes": special_notes,
    }
