"""
Mock export document/paperwork requirements per destination country.
Stand-in for a real source (e.g. DGFT export documentation guidelines,
country-specific customs authority requirements) until one is
integrated.

Deliberately scoped to customs/shipping paperwork (commercial invoice,
packing list, bill of lading, certificate of origin, etc.) -- NOT
product certifications or quality standards, which are already covered
by capability_requirements.py / the Capability Gap Agent. Keeping these
separate avoids two agents answering overlapping questions differently.

Deterministic lookup data, like the other _data.py sources -- required
documents for a given market are reference data, not a judgment call.
"""

# mandatory: documents needed for essentially every shipment to this market.
# conditional: documents needed only in specific circumstances, with the
#   condition spelled out so the exporter knows when it applies.
_DOCUMENT_REQUIREMENTS = {
    "US": {
        "mandatory": [
            "Commercial Invoice",
            "Packing List",
            "Bill of Lading / Airway Bill",
            "Shipping Bill (Indian customs)",
        ],
        "conditional": [
            {
                "name": "Certificate of Origin (non-preferential)",
                "condition": "If the buyer or broker requests proof of Indian origin for their own records.",
            },
            {
                "name": "FDA Prior Notice",
                "condition": "If the shipment includes any FDA-regulated goods.",
            },
        ],
        "notes": (
            "US customs does not require a Certificate of Origin for "
            "standard MFN-rate imports, but buyers/brokers often request "
            "one anyway for their own compliance records."
        ),
    },
    "DE": {
        "mandatory": [
            "Commercial Invoice",
            "Packing List",
            "Bill of Lading / Airway Bill",
            "Shipping Bill (Indian customs)",
            "EUR.1 Movement Certificate or Certificate of Origin",
        ],
        "conditional": [
            {
                "name": "REACH Compliance Declaration",
                "condition": "If the product falls under EU REACH chemical regulations.",
            },
        ],
        "notes": (
            "EU customs generally expects a Certificate of Origin for all "
            "non-EU imports, regardless of FTA status."
        ),
    },
    "AE": {
        "mandatory": [
            "Commercial Invoice",
            "Packing List",
            "Bill of Lading / Airway Bill",
            "Shipping Bill (Indian customs)",
            "Certificate of Origin (CEPA)",
        ],
        "conditional": [
            {
                "name": "Chamber of Commerce Attestation",
                "condition": "Required for the Certificate of Origin to be accepted under CEPA preferential treatment.",
            },
        ],
        "notes": (
            "To claim the India-UAE CEPA preferential tariff rate, the "
            "Certificate of Origin must be issued under CEPA rules of "
            "origin and attested as required -- a standard non-preferential "
            "Certificate of Origin will not qualify for the preferential rate."
        ),
    },
}

# Documents needed for essentially any international shipment, used
# when a country isn't in the table above.
_DEFAULT_MANDATORY = [
    "Commercial Invoice",
    "Packing List",
    "Bill of Lading / Airway Bill",
    "Shipping Bill (Indian customs)",
]

_DEFAULT_NOTES = (
    "No country-specific document data on file for this market -- "
    "the list above covers standard international shipment paperwork "
    "only. Verify additional requirements with a customs broker before "
    "shipping."
)


def get_document_requirements(country: str) -> dict:
    entry = _DOCUMENT_REQUIREMENTS.get(country.upper())

    if entry is None:
        return {
            "mandatory": _DEFAULT_MANDATORY,
            "conditional": [],
            "notes": _DEFAULT_NOTES,
        }

    return entry
