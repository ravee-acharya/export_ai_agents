"""
Mock knowledge base of certification/capability requirements per
sector and target market. Stand-in for real regulatory/standards data
until this is sourced from a live compliance database.

Maintained the same way as scheme_knowledge_base.py: hand-curated,
updated on policy/standard changes rather than swapped for a live API,
since these requirements don't change daily.
"""

_REQUIREMENTS = {
    "textiles": {
        "US": [
            "CPSIA compliance (flammability/lead testing for textiles)",
            "ISO 9001 (quality management)",
        ],
        "DE": [
            "OEKO-TEX Standard 100",
            "EU REACH chemical compliance",
            "ISO 9001 (quality management)",
        ],
        "GB": [
            "UKCA marking where applicable",
            "ISO 9001 (quality management)",
        ],
        "AE": [
            "ISO 9001 (quality management)",
        ],
    },
}

# Requirements applied regardless of sector/country match above.
_DEFAULT_REQUIREMENTS = [
    "ISO 9001 (quality management)",
]


def get_capability_requirements(sector: str, country: str) -> list[str]:
    sector_map = _REQUIREMENTS.get(sector, {})
    return sector_map.get(country.upper(), _DEFAULT_REQUIREMENTS)
